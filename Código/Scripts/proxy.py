import paho.mqtt.client as mqtt
import json
import signal
import threading
import time
import sys

# Define list of OBUs and central broker
obu_brokers = [
    {"id": "OBU1", "host": "192.168.98.10", "port": 1883},
    {"id": "OBU2", "host": "192.168.98.20", "port": 1883},
    {"id": "OBU3", "host": "192.168.98.30", "port": 1883},
]
central_broker = {"host": "192.168.98.40", "port": 1883}

# Shutdown flag
running = True

# Try connecting to central broker
try:
    central_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    central_client.connect(central_broker["host"], central_broker["port"])
    central_client.loop_start()
    print(f"[{time.strftime('%H:%M:%S')}] Connected to central broker at {central_broker['host']}:{central_broker['port']}")
except Exception as e:
    print(f"[ERROR] Failed to connect to central broker: {e}")
    sys.exit(1)

# Track all OBU clients for cleanup
obu_clients = []

# Helper to create message callback
def make_on_message(obu_id):
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic

            # Processar CAMs
            if "cam" in topic:
                lat = payload.get("latitude")
                lon = payload.get("longitude")

                if lat is not None and lon is not None:
                    simplified_msg = {
                        "obu_id": obu_id,
                        "latitude": lat,
                        "longitude": lon
                    }

                    if central_client.is_connected():
                        central_client.publish("frontend/obu_position", json.dumps(simplified_msg))
                        print(f"[{obu_id}][{time.strftime('%H:%M:%S')}] Published CAM to frontend: {simplified_msg}")
                    else:
                        print(f"[{obu_id}] Central broker not connected. Skipping CAM publish.")
                else:
                    print(f"[{obu_id}] Received CAM message without position")

            # Processar DENMs
            elif "denm" in topic:
                event_position = payload.get("fields", {}).get("denm", {}).get("management", {}).get("eventPosition", {})
                lat = event_position.get("latitude")
                lon = event_position.get("longitude")

                if lat is not None and lon is not None:
                    simplified_msg = {
                        "obu_id": obu_id,
                        "latitude": lat,
                        "longitude": lon,
                        "type": "denm"
                    }

                    if central_client.is_connected():
                        central_client.publish("frontend/obu_position", json.dumps(simplified_msg))
                        print(f"[{obu_id}][{time.strftime('%H:%M:%S')}] Published DENM to frontend: {simplified_msg}")
                    else:
                        print(f"[{obu_id}] Central broker not connected. Skipping DENM publish.")
                else:
                    print(f"[{obu_id}] Received DENM message without position")

            else:
                print(f"[{obu_id}] Unknown message type received on topic {topic}")

        except Exception as e:
            print(f"[ERROR] Processing message from {obu_id}: {e}")
    return on_message

# on_disconnect for OBU clients
def make_on_disconnect(obu_id):
    def on_disconnect(client, userdata, rc):
        print(f"[{obu_id}] Disconnected with result code {rc}")
    return on_disconnect

# Connect to each OBU broker
for obu in obu_brokers:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = make_on_message(obu["id"])
        client.on_disconnect = make_on_disconnect(obu["id"])

        # Set Last Will message
        client.will_set(f"status/{obu['id']}", payload="offline", retain=True)

        client.connect(obu["host"], obu["port"])
        client.loop_start()
        client.subscribe("vanetza/out/#")  # subscribe after loop_start
        obu_clients.append(client)

        print(f"[{time.strftime('%H:%M:%S')}] Connected and subscribed to {obu['id']} at {obu['host']}:{obu['port']}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to {obu['id']} at {obu['host']}: {e}")

# Graceful shutdown
def shutdown(signum, frame):
    global running
    print("\n[SHUTDOWN] Stopping all clients...")
    running = False

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Keep alive loop
try:
    while running:
        time.sleep(1)
except KeyboardInterrupt:
    shutdown(None, None)

# Cleanup
for client in obu_clients:
    client.loop_stop()
    client.disconnect()

central_client.loop_stop()
central_client.disconnect()

print(f"[{time.strftime('%H:%M:%S')}] All MQTT clients disconnected. Bye!")
