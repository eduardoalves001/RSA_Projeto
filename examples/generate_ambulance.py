import json
import paho.mqtt.client as mqtt
import threading
from time import sleep
import gpxpy
from geopy.distance import geodesic
import os

# ========== CONFIGURAÇÕES ==========
GPX_FILE = 'static/routes/rota_wok_glicinias.gpx'
MQTT_BROKER = '192.168.98.20'
MQTT_PORT = 1883
DENM_TOPIC_OUT = 'vanetza/out/denm'
CAM_TOPIC_IN = 'vanetza/in/cam'
CAM_TOPIC_OUT = 'vanetza/out/cam'
SLEEP_INTERVAL = 2  # segundos entre envios de CAM
DISTANCE_THRESHOLD = 5  # metros para considerar "chegou" no acidente
# ===================================

# ---------- Dados Globais ----------
trajectory = []
target_position = None
current_index = 0

lock = threading.Lock()
other_obu_position_lock = threading.Lock()
other_obu_positions = {}

# ---------- Função para carregar GPX ----------
def load_gpx_coordinates(gpx_path):
    try:
        with open(gpx_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            coords = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        coords.append((point.latitude, point.longitude))
            return coords
    except Exception as e:
        print(f"[ERROR] Failed to load GPX file: {e}")
        return []

trajectory = load_gpx_coordinates(GPX_FILE)
print(f"[INIT] Loaded {len(trajectory)} points from GPX file")

# ---------- Callbacks MQTT ----------
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(DENM_TOPIC_OUT)  # Escuta DENMs dos outros veículos
    client.subscribe(CAM_TOPIC_OUT)  # Escuta CAMs dos outros veículos

def on_message(client, userdata, msg):
    global target_position
    try:
        payload = json.loads(msg.payload.decode('utf-8'))

        if msg.topic == DENM_TOPIC_OUT:
            lat = payload.get("latitude")
            lon = payload.get("longitude")
            if lat is not None and lon is not None:
                with lock:
                    target_position = (lat, lon)
                print(f"[DENM RECEIVED] New accident position: {target_position}")

        elif msg.topic == CAM_TOPIC_OUT:
            sender_lat = payload.get("latitude")
            sender_lon = payload.get("longitude")
            if sender_lat is not None and sender_lon is not None:
                with lock:
                    cam_position = (sender_lat, sender_lon)
                print(f"[CAM RECEIVED] Position from other Car: {cam_position}")

    except Exception as e:
        print(f"[ERROR] Failed to process incoming message: {e}")

# ---------- Movimento da ambulância e envio de CAMs ----------
def follow_route_and_send_cams(client):
    global current_index

    while current_index < len(trajectory):
        with lock:
            my_pos = trajectory[current_index]
            local_target_pos = target_position

        if local_target_pos is None:
            print(f"[MOVE] No accident yet, at {my_pos}")
        else:
            dist_to_accident = geodesic(my_pos, local_target_pos).meters
            print(f"[MOVE] At {my_pos}, distance to accident: {dist_to_accident:.1f}m")

            if dist_to_accident <= DISTANCE_THRESHOLD:
                print("[ARRIVED] Reached accident location.")
                sleep(SLEEP_INTERVAL)
                continue

            next_index = min(current_index + 1, len(trajectory) - 1)
            dist_next_point = geodesic(trajectory[next_index], local_target_pos).meters

            if dist_next_point < dist_to_accident:
                current_index = next_index
            else:
                print("[WAIT] Holding position to avoid moving away from accident")

        try:
            if not os.path.exists('in_cam.json'):
                print("[ERROR] CAM template file 'in_cam.json' not found.")
                break

            with open('in_cam.json') as f:
                cam_msg = json.load(f)
            cam_msg["latitude"] = my_pos[0]
            cam_msg["longitude"] = my_pos[1]

            client.publish(CAM_TOPIC_IN, json.dumps(cam_msg))
            print(f"[CAM SENT BY AMBULANCE] lat={my_pos[0]}, lon={my_pos[1]}")

        except Exception as e:
            print(f"[ERROR] Failed to send CAM: {e}")

        sleep(SLEEP_INTERVAL)

    print("[COMPLETE] Finished trajectory")

# ---------- Setup MQTT ----------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ---------- Rodar MQTT Loop e movimento ----------
mqtt_thread = threading.Thread(target=client.loop_forever, daemon=True)
mqtt_thread.start()

try:
    follow_route_and_send_cams(client)
except KeyboardInterrupt:
    print("[EXIT] Interrupted by user")

client.disconnect()
mqtt_thread.join()