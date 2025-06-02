import math

vehicles = [
    # Carros na faixa superior (lat ~ 41.0)
    {"id": 1, "lon": -8.610, "lat": 41.000, "target_lat": 41.000, "type": "car", "state": "active"},
    {"id": 2, "lon": -8.608, "lat": 41.000, "target_lat": 41.000, "type": "car", "state": "active"},
    {"id": 3, "lon": -8.606, "lat": 41.000, "target_lat": 41.000, "type": "car", "state": "active"},

    # Carros na faixa inferior (lat ~ 40.998)
    {"id": 4, "lon": -8.609, "lat": 40.998, "target_lat": 40.998, "type": "car", "state": "active"},
    {"id": 5, "lon": -8.607, "lat": 40.998, "target_lat": 40.998, "type": "car", "state": "active"},
    {"id": 6, "lon": -8.603, "lat": 40.998, "target_lat": 40.998, "type": "car", "state": "active"},

    # Ambulância
    {"id": 7, "lon": -8.610, "lat": 40.998, "target_lat": 40.998, "type": "ambulance", "state": "active"},

    # Acidente (na faixa inferior)
    {"id": 8, "lon": -8.605, "lat": 40.998, "type": "car", "state": "crashed"},
]

# Posicao do acidente em lat/lon
ACCIDENT_POS = (-8.605, 40.999)  # lon, lat
ACCIDENT_RADIUS_METERS = 100  # raio de 100 metros

# Haversine para distancia em metros entre dois pontos lat/lon
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # raio da Terra em metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # distância em metros

def distance(vehicle, pos):
    return haversine(vehicle["lon"], vehicle["lat"], pos[0], pos[1])

def is_path_clear(vehicle, vehicles, min_distance_m=50):
    for other in vehicles:
        if other["id"] == vehicle["id"]:
            continue
        # Verifica se estão na mesma faixa (aproximando latitudes)
        same_lane = abs(vehicle["lat"] - other["lat"]) < 0.0001  # cerca de 11m de tolerância
        in_front = other["lon"] > vehicle["lon"]
        dist = haversine(vehicle["lon"], vehicle["lat"], other["lon"], other["lat"])
        if same_lane and in_front and dist < min_distance_m:
            return False
    return True

def update_simulation():
    speed_m_s = 5  # velocidade em metros por segundo
    lane_change_speed_deg = 0.00001  # velocidade de mudança de faixa em graus latitude (aprox 1.11 m)

    max_lon = -8.590  # longitude máxima para reset (limite direito da "pista")
    min_lon = -8.615  # longitude mínima para reset (limite esquerdo)

    for v in vehicles:
        if v["state"] == "crashed":
            continue

        # Reset do veículo quando ultrapassa o limite direito (lon > max_lon)
        if v["lon"] > max_lon:
            v["lon"] = min_lon
            # Resetar faixa original
            if abs(v["lat"] - 41.000) < 0.0001:
                v["lat"] = v["target_lat"] = 41.000
            else:
                v["lat"] = v["target_lat"] = 40.998

        # Movimento vertical suave (mudar faixa)
        if v["lat"] < v["target_lat"]:
            v["lat"] += lane_change_speed_deg
            if v["lat"] > v["target_lat"]:
                v["lat"] = v["target_lat"]
        elif v["lat"] > v["target_lat"]:
            v["lat"] -= lane_change_speed_deg
            if v["lat"] < v["target_lat"]:
                v["lat"] = v["target_lat"]

        if v["type"] == "ambulance":
            if is_path_clear(v, vehicles, min_distance_m=50):
                if v["lon"] < ACCIDENT_POS[0]:
                    # Avança em longitude (direita)
                    v["lon"] += 0.00005  # approx 5m em longitude (depende da latitude)
                # Ajusta latitude para ir até o acidente
                if v["target_lat"] != ACCIDENT_POS[1]:
                    v["target_lat"] = ACCIDENT_POS[1]
            continue

        if v["type"] == "car":
            crash_lane_lat = 40.998
            safe_lane_lat = 41.000
            distance_to_crash = haversine(v["lon"], v["lat"], ACCIDENT_POS[0], ACCIDENT_POS[1])
            is_approaching = 0 < (ACCIDENT_POS[0] - v["lon"]) < 0.0015  # cerca de 150m em longitude aprox
            passed = v["lon"] > ACCIDENT_POS[0] + 0.0003  # passou o acidente (aprox 30m)

            if abs(v["lat"] - crash_lane_lat) < 0.00005 and is_approaching:
                # tenta mudar para faixa segura se caminho livre
                temp_v = {"id": v["id"], "lon": v["lon"], "lat": safe_lane_lat}
                if is_path_clear(temp_v, vehicles):
                    v["target_lat"] = safe_lane_lat

            if passed and v["lat"] != v["target_lat"]:
                # Voltar para faixa original suavemente
                if v["lat"] > v["target_lat"]:
                    v["lat"] -= lane_change_speed_deg
                elif v["lat"] < v["target_lat"]:
                    v["lat"] += lane_change_speed_deg

            if is_path_clear(v, vehicles):
                # Avança na longitude
                v["lon"] += 0.00002  # approx 2m por frame

def get_vehicle_states():
    return vehicles
