from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt
import threading
import json
import time

app = Flask(__name__, static_folder='static', template_folder='templates')

# Estado global dos veículos
vehicle_states = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/vehicles")
def get_vehicles():
    now = time.time()
    # Filtra veículos que enviaram dados recentemente (últimos 10s)
    return jsonify({
        vid: state
        for vid, state in vehicle_states.items()
        if now - state.get("timestamp", 0) < 10
    })

# Callback ao receber mensagens MQTT
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[ERROR] JSON inválido de {topic}: {payload}")
        return

    # Processar mensagens do tópico frontend/obu_position
    if topic == "frontend/obu_position":
        vehicle_id = data.get("obu_id")
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if vehicle_id and latitude and longitude:
            if vehicle_id not in vehicle_states:
                vehicle_states[vehicle_id] = {}

            vehicle_states[vehicle_id]["position"] = {
                "lat": latitude,
                "lng": longitude
            }
            vehicle_states[vehicle_id]["timestamp"] = time.time()
            print(f"[MQTT] {vehicle_id} - posição atualizada: {data}")
        else:
            print(f"[WARN] Mensagem de posição inválida: {data}")
        return

    # Processar mensagens dos tópicos vanetza/in/cam e vanetza/out/cam
    parts = topic.split('/')
    if len(parts) < 3:
        return

    if "obu" in parts[1]:
        vehicle_id = parts[1]
        message_type = parts[2]
    else:
        vehicle_id = "obu1"
        message_type = "denm"

    if vehicle_id not in vehicle_states:
        vehicle_states[vehicle_id] = {}

    if message_type == "cam":
        if "latitude" in data and "longitude" in data:
            vehicle_states[vehicle_id]["position"] = {
                "lat": data["latitude"],
                "lng": data["longitude"]
            }
            vehicle_states[vehicle_id]["speed"] = data.get("speed", 0)
            vehicle_states[vehicle_id]["timestamp"] = time.time()
        else:
            print(f"[WARN] CAM sem coordenadas de {vehicle_id}")

    elif message_type == "denm":
        try:
            event_position = data.get("fields", {}).get("denm", {}).get("management", {}).get("eventPosition", {})
            latitude = event_position.get("latitude")
            longitude = event_position.get("longitude")

            if latitude is not None and longitude is not None:
                vehicle_states[vehicle_id]["position"] = {
                    "lat": latitude,
                    "lng": longitude
                }
                vehicle_states[vehicle_id]["accident"] = True
                vehicle_states[vehicle_id]["denm_timestamp"] = time.time()
            else:
                print(f"[WARN] DENM sem coordenadas de {vehicle_id}")
        except KeyError as e:
            print(f"[ERROR] DENM malformado de {vehicle_id}: {e}")

    print(f"[MQTT] {vehicle_id} - {message_type}: {data}")

# Thread para escutar o broker MQTT
def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("192.168.98.40", 1883, 60)

    # Subscreve aos tópicos que queres ouvir
    client.subscribe("vanetza/in/cam")
    client.subscribe("vanetza/out/cam")
    client.subscribe("vanetza/in/denm")
    client.subscribe("vanetza/out/denm")
    client.subscribe("frontend/obu_position")  # Adicionado para receber posições dos OBUs

    client.loop_forever()

if __name__ == "__main__":
    t = threading.Thread(target=mqtt_thread)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=5000)