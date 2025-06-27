import json
import paho.mqtt.client as mqtt
import threading
from time import sleep
import gpxpy

# ========== CONFIGURATION ==========
GPX_FILE = 'static/routes/rota_wok_glicinias.gpx'
DENM_TEMPLATE_FILE = 'in_denm.json'
MQTT_BROKER = '192.168.98.10' # O carro que teve o acidente fica com a OBU 1
MQTT_PORT = 1883
DENM_TOPIC_IN = 'vanetza/in/denm'
SLEEP_INTERVAL = 3  # seconds between repeated DENM messages
# ===================================

def get_fixed_position_from_gpx(gpx_path):
    with open(gpx_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

        # Tentar obter um ponto intermediário no segmento
        for track in gpx.tracks:
            for segment in track.segments:
                if segment.points:
                    midpoint_index = len(segment.points) // 2  # Índice do ponto intermediário
                    midpoint = segment.points[midpoint_index]
                    return (midpoint.latitude, midpoint.longitude)

        # Fallback: último waypoint
        if gpx.waypoints:
            point = gpx.waypoints[-1]
            return (point.latitude, point.longitude)

    raise ValueError("GPX file has no valid coordinates.")


accident_position = get_fixed_position_from_gpx(GPX_FILE)
print(f"[INIT] Accident fixed at: {accident_position}")

# ---------- MQTT Setup ----------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    print("[MQTT] Connected with result code", rc)

client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ---------- DENM Sender ----------
def send_denm():
    try:
        with open(DENM_TEMPLATE_FILE, 'r') as f:
            denm = json.load(f)

        # Update DENM with accident position
        denm["latitude"] = accident_position[0]
        denm["longitude"] = accident_position[1]

        # Send DENM repeatedly
        while True:
            payload = json.dumps(denm)
            client.publish(DENM_TOPIC_IN, payload)
            print(f"[DENM SENT] lat={denm['latitude']}, lon={denm['longitude']}")
            sleep(SLEEP_INTERVAL)
    except Exception as e:
        print(f"[ERROR] Failed to send DENM: {e}")

# ---------- Start MQTT + Sender ----------
threading.Thread(target=client.loop_forever, daemon=True).start()
sleep(2)
send_denm()
