import time
import json
import paho.mqtt.client as mqtt
import threading
from time import sleep
import gpxpy
import os

# ========== CONFIGURAÇÕES ==========
NORMAL_GPX_FILE = 'static/routes/rota.gpx'
DESVIO_GPX_FILE = 'static/routes/rota_alternativa.gpx'

MQTT_BROKER = '192.168.98.30'
MQTT_PORT = 1883
DENM_TOPIC_OUT = 'vanetza/out/#'
CAM_TOPIC_IN = 'vanetza/in/cam'
CAM_TOPIC_OUT = 'vanetza/out/cam'

SLEEP_INTERVAL = 2  # segundos entre envios de CAM
# ===================================

# ---------- Dados Globais ----------
current_trajectory = []
current_index = 0
diverted = False
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

current_trajectory = load_gpx_coordinates(NORMAL_GPX_FILE)
print(f"[INIT] Loaded {len(current_trajectory)} points from NORMAL route")

# ---------- Callbacks MQTT ----------
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(DENM_TOPIC_OUT) # Escuta DENMs enviados por outros veículos
    client.subscribe(CAM_TOPIC_OUT)  # Escuta CAMs enviados por outros veículos

def on_message(client, userdata, msg):
    global current_trajectory, current_index, diverted
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        topic = msg.topic

        if "denm" in topic and not diverted:
            event_position = payload.get("fields", {}).get("denm", {}).get("management", {}).get("eventPosition", {})
            lat = event_position.get("latitude")
            lon = event_position.get("longitude")
            if lat is not None and lon is not None:
                print(f"[DENM RECEIVED] Accident at ({lat}, {lon}) — Switching to diversion route")
                with lock:
                    current_trajectory = load_gpx_coordinates(DESVIO_GPX_FILE)
                    current_index = 0
                    diverted = True
            else:
                print("[WARN] DENM message missing coordinates")

        elif "cam" in topic:
            sender_lat = payload.get("latitude")
            sender_lon = payload.get("longitude")
            if sender_lat is not None and sender_lon is not None:
                with lock:
                    cam_position = (sender_lat, sender_lon)
                print(f"[CAM RECEIVED] Position from Ambulance: {cam_position}")

    except Exception as e:
        print(f"[ERROR] Failed to process incoming message: {e}")
# ---------- Movimento do carro e envio de CAMs ----------
def follow_route_and_send_cams(client):
    global current_index, current_trajectory, diverted

    print("[START] Starting to follow the route")
    while True:
        with lock:
            if current_index >= len(current_trajectory):
                if diverted:
                    print("[COMPLETE] Finished diversion route")
                else:
                    print("[COMPLETE] Finished normal route")
                break

            my_pos = current_trajectory[current_index]
            current_index += 1

        # Preparar e enviar CAM com a posição atual
        try:
            if not os.path.exists('in_cam.json'):
                print("[ERROR] CAM template file 'in_cam.json' not found.")
                break

            with open('in_cam.json') as f:
                cam_msg = json.load(f)
            cam_msg["latitude"] = my_pos[0]
            cam_msg["longitude"] = my_pos[1]

            client.publish(CAM_TOPIC_IN, json.dumps(cam_msg))

            if diverted:
                print(f"[CAM SENT - DIVERTED ROUTE] lat={my_pos[0]}, lon={my_pos[1]}")
            else:
                print(f"[CAM SENT - NORMAL ROUTE] lat={my_pos[0]}, lon={my_pos[1]}")

        except Exception as e:
            print(f"[ERROR] Failed to send CAM: {e}")

        sleep(SLEEP_INTERVAL)


# ---------- Setup MQTT ----------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
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