import math

vehicles = [
    # Carros na faixa superior (y = 130)
    {"id": 1, "x": 50, "y": 130, "target_y": 130, "type": "car", "state": "active"},
    {"id": 2, "x": 150, "y": 130, "target_y": 130, "type": "car", "state": "active"},
    {"id": 3, "x": 250, "y": 130, "target_y": 130,"type": "car", "state": "active"},
    {"id": 4, "x": 350, "y": 130, "target_y": 130,"type": "car", "state": "active"},
    {"id": 5, "x": 450, "y": 130, "target_y": 130,"type": "car", "state": "active"},
    {"id": 6, "x": 550, "y": 130, "target_y": 130,"type": "car", "state": "active"},
    {"id": 7, "x": 650, "y": 130, "target_y": 130,"type": "car", "state": "active"},
    {"id": 8, "x": 750, "y": 130, "target_y": 130,"type": "car", "state": "active"},

    # Carros na faixa inferior (y = 230)
    {"id": 9, "x": 100, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 10, "x": 200, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 12, "x": 400, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 13, "x": 500, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 14, "x": 600, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 15, "x": 700, "y": 230, "target_y": 230,"type": "car", "state": "active"},
    {"id": 16, "x": 800, "y": 230, "target_y": 230,"type": "car", "state": "active"},

    # Ambulância (a única ambulância)
    {"id": 25, "x": 20, "y": 230, "target_y": 230, "type": "ambulance", "state": "active"},

    # Acidente (na faixa inferior)
    {"id": 26, "x": 300, "y": 230, "type": "car", "state": "crashed"},
]


ACCIDENT_POS = (300, 180)
ACCIDENT_RADIUS = 100


def distance(v1, v2):
    return math.hypot(v1["x"] - v2[0], v1["y"] - v2[1])

def update_simulation():
    speed = 2
    lane_change_speed = 2  # pixels per frame to shift vertically

    for v in vehicles:
        if v["state"] == "crashed":
            continue
               
        # Dar reset aos carros
        if v["x"] > 800:
            v["x"] = -30  # Just off-screen on the left
            v["target_y"] = v["y"] = 230 if v["y"] < 200 else 130  # Randomly or alternately reset lane


        # Smooth Y movement
        if v["y"] < v["target_y"]:
            v["y"] += min(lane_change_speed, v["target_y"] - v["y"])
        elif v["y"] > v["target_y"]:
            v["y"] -= min(lane_change_speed, v["y"] - v["target_y"])

        if v["type"] == "ambulance":
            if is_path_clear(v, vehicles, min_distance=50):
                if v["x"] < ACCIDENT_POS[0]:
                    v["x"] += 5
                if v["target_y"] > ACCIDENT_POS[1]:
                    v["target_y"] = ACCIDENT_POS[1]
                elif v["target_y"] < ACCIDENT_POS[1]:
                    v["target_y"] = ACCIDENT_POS[1]
            continue

        if v["type"] == "car":
            crash_lane = 230
            safe_lane = 130
            distance_to_crash = ACCIDENT_POS[0] - v["x"]
            is_approaching = 0 < distance_to_crash < 150
            passed = v["x"] > ACCIDENT_POS[0] + 30  # Car has passed the accident area

            if v["y"] == crash_lane and is_approaching:
                # Propose lane switch if safe
                temp_v = {"id": v["id"], "x": v["x"], "y": safe_lane}
                if is_path_clear(temp_v, vehicles):
                    v["target_y"] = safe_lane

            if passed and v["y"] != v["target_y"]:
                # Move smoothly back to original lane once passed the accident
                if v["y"] > v["target_y"]:
                    v["y"] += min(lane_change_speed, v["y"] - v["target_y"])
                elif v["y"] < v["target_y"]:
                    v["y"] -= min(lane_change_speed, v["y"] - v["target_y"])

            if is_path_clear(v, vehicles):
                v["x"] += speed


def get_vehicle_states():
    return vehicles

def is_path_clear(vehicle, vehicles, min_distance=50):
    for other in vehicles:
        if other["id"] == vehicle["id"]:
            continue
        same_lane = vehicle["y"] == other["y"]
        in_front = other["x"] > vehicle["x"]
        too_close = abs(other["x"] - vehicle["x"]) < min_distance
        if same_lane and in_front and too_close:
            return False
    return True

