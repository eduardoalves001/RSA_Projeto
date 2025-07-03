import json
import paho.mqtt.client as mqtt
import threading
from time import sleep
import gpxpy
from geopy.distance import geodesic
import os

# ========== CONFIGURAÇÕES ==========
GPX_FILE           = 'static/routes/rota.gpx'
MQTT_BROKER        = '192.168.98.20'
MQTT_PORT          = 1883
DENM_TOPIC_OUT     = 'vanetza/out/denm'
CAM_TOPIC_IN       = 'vanetza/in/cam'
CAM_TOPIC_OUT      = 'vanetza/out/cam'
SLEEP_INTERVAL     = 2    # segundos entre envios de CAM
DISTANCE_THRESHOLD = 5    # metros para considerar "chegou"
START_OFFSET       = 1   # começa 15 pontos à frente no GPX
# ===================================

# ---------- Dados Globais ----------
trajectory = []
target_position = None
current_index = 0

lock                    = threading.Lock()
other_obu_position_lock = threading.Lock()
other_obu_positions     = {}

# ---------- Função para carregar GPX ----------
def load_gpx_coordinates(gpx_path):
    try:
        with open(gpx_path, 'r') as gpx_file:
            gpx    = gpxpy.parse(gpx_file)
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

# Apply start offset
current_index = min(START_OFFSET, len(trajectory) - 1)
print(f"[INIT] Starting at GPX index {current_index}: {trajectory[current_index]}")

# ---------- Callbacks MQTT ----------
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(DENM_TOPIC_OUT)  # ouvir DENM de outros
    client.subscribe(CAM_TOPIC_OUT)   # ouvir CAM de outros

def on_message(client, userdata, msg):
    global target_position
    try:
        payload = json.loads(msg.payload.decode('utf-8'))

        if msg.topic == DENM_TOPIC_OUT:
            # Extract latitude and longitude from nested structure
            event_position = payload.get("fields", {}).get("denm", {}).get("management", {}).get("eventPosition", {})
            lat = event_position.get("latitude")
            lon = event_position.get("longitude")
            if lat is not None and lon is not None:
                with lock:
                    target_position = (lat, lon)
                print(f"[DENM RECEIVED] Accident at {target_position}")
            else:
                print("[WARN] DENM message missing coordinates")
        elif msg.topic == CAM_TOPIC_OUT:
            sender_lat = payload.get("latitude")
            sender_lon = payload.get("longitude")
            if sender_lat is not None and sender_lon is not None:
                with other_obu_position_lock:
                    other_obu_positions[msg.topic] = (sender_lat, sender_lon)
                print(f"[CAM RECEIVED] Other vehicle at {(sender_lat, sender_lon)}")

    except Exception as e:
        print(f"[ERROR] Failed to process incoming message: {e}")

# ---------- Movimento & envio de CAMs ----------
def follow_route_and_send_cams(client):
    global current_index

    while current_index < len(trajectory):
        with lock:
            my_pos = trajectory[current_index]
            local_target = target_position

        # Se ainda não há DENM
        if local_target is None:
            print(f"[MOVE] No accident yet, at {my_pos}")
        else:
            dist_to_acc = geodesic(my_pos, local_target).meters
            print(f"[MOVE] At {my_pos}, dist to accident: {dist_to_acc:.1f}m")
            if dist_to_acc <= DISTANCE_THRESHOLD:
                print("[ARRIVED] Reached accident location.")
                break  # Stop movement once the accident location is reached

        # Prepara e envia CAM
        try:
            if not os.path.exists('in_cam.json'):
                print("[ERROR] CAM template file 'in_cam.json' not found.")
                break

            with open('in_cam.json') as f:
                cam_msg = json.load(f)

            cam_msg["latitude"] = my_pos[0]
            cam_msg["longitude"] = my_pos[1]

            client.publish(CAM_TOPIC_IN, json.dumps(cam_msg))
            print(f"[CAM SENT] lat={my_pos[0]}, lon={my_pos[1]}")
        except Exception as e:
            print(f"[ERROR] Failed to send CAM: {e}")

        current_index += 1
        sleep(SLEEP_INTERVAL)

    print("[COMPLETE] Finished trajectory")

# ---------- Setup MQTT & executar ----------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Inicia loop MQTT em background
mqtt_thread = threading.Thread(target=client.loop_forever, daemon=True)
mqtt_thread.start()

# Inicia movimento + CAMs
try:
    follow_route_and_send_cams(client)
except KeyboardInterrupt:
    print("[EXIT] Interrupted by user")

client.disconnect()
mqtt_thread.join()
