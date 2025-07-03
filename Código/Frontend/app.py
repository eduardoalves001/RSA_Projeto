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
    return jsonify({
        vid: state
        for vid, state in vehicle_states.items()
        if now - state.get("timestamp", 0) < 10
    })

# Função utilitária para converter coordenadas se vierem em micrograus
def convert_coord(value):
    # Se estiver fora de intervalo típico de graus (-90 a 90 ou -180 a 180), converte
    if abs(value) > 180:
        return value / 1e7
    return value

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[ERROR] JSON inválido de {topic}: {payload}")
        return

    if topic == "frontend/obu_position":
        vehicle_id = data.get("obu_id")
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if vehicle_id and latitude is not None and longitude is not None:
            latitude = convert_coord(latitude)
            longitude = convert_coord(longitude)

            if vehicle_id not in vehicle_states:
                vehicle_states[vehicle_id] = {}

            vehicle_states[vehicle_id]["position"] = {
                "lat": latitude,
                "lng": longitude
            }
            vehicle_states[vehicle_id]["timestamp"] = time.time()
            print(f"[MQTT] {vehicle_id} - posição atualizada: {latitude}, {longitude}")
        else:
            print(f"[WARN] Mensagem de posição inválida: {data}")
        return

    # Processar mensagens dos tópicos vanetza/in/cam e vanetza/in/denm
    parts = topic.split('/')
    if len(parts) < 3:
        return

    vehicle_id = parts[1] if "obu" in parts[1] else "obu1"
    message_type = parts[2]

    if vehicle_id not in vehicle_states:
        vehicle_states[vehicle_id] = {}

    if message_type == "cam":
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is not None and longitude is not None:
            latitude = convert_coord(latitude)
            longitude = convert_coord(longitude)

            vehicle_states[vehicle_id]["position"] = {
                "lat": latitude,
                "lng": longitude
            }
            vehicle_states[vehicle_id]["speed"] = data.get("speed", 0)
            vehicle_states[vehicle_id]["timestamp"] = time.time()
            print(f"[MQTT][CAM] {vehicle_id} posição: {latitude}, {longitude}")
        else:
            print(f"[WARN] CAM sem coordenadas de {vehicle_id}: {data}")

    elif message_type == "denm":
        try:
            event_position = data.get("fields", {}).get("denm", {}).get("management", {}).get("eventPosition", {})
            latitude = event_position.get("latitude")
            longitude = event_position.get("longitude")

            if latitude is not None and longitude is not None:
                latitude = convert_coord(latitude)
                longitude = convert_coord(longitude)

                vehicle_states[vehicle_id]["accident_position"] = {
                    "lat": latitude,
                    "lng": longitude
                }
                vehicle_states[vehicle_id]["accident"] = True
                vehicle_states[vehicle_id]["timestamp"] = time.time()
                print(f"[MQTT][DENM] Acidente reportado por {vehicle_id} em ({latitude}, {longitude})")
            else:
                print(f"[WARN] DENM sem coordenadas de {vehicle_id}")
        except KeyError as e:
            print(f"[ERROR] DENM malformado de {vehicle_id}: {e}")

# Thread para escutar MQTT
def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("192.168.98.40", 1883, 60)

    client.subscribe("vanetza/in/cam")
    client.subscribe("vanetza/out/cam")
    client.subscribe("vanetza/in/denm")
    client.subscribe("vanetza/out/denm")
    client.subscribe("frontend/obu_position")

    client.loop_forever()

if __name__ == "__main__":
    t = threading.Thread(target=mqtt_thread)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=5000)
