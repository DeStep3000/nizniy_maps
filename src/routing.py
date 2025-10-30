import pandas as pd
import random
from geopy.distance import geodesic

from src.logger import log_user_action


def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).meters


def calculate_walking_time(distance_meters):
    walking_speed_kmh = 5
    walking_speed_ms = walking_speed_kmh * 1000 / 3600
    time_minutes = (distance_meters / walking_speed_ms) / 60
    return time_minutes // 1 + 1


def calculate_score(object_data, user_categories, current_position, search_radius, max_distance=2000):
    if pd.isna(object_data["lat"]) or pd.isna(object_data["lon"]):
        return 0, 999999, 999999

    obj_coord = (object_data["lat"], object_data["lon"])
    distance = calculate_distance(current_position, obj_coord)

    if distance > max_distance or distance > search_radius:
        return 0, 999999, 999999

    category_match = 1 if object_data["category_id"] in user_categories else 0
    visit_time = 20
    distance_km = distance / 1000
    score = category_match / (distance_km + 0.1)

    return score, distance, visit_time


def plan_route(start_position, user_categories, total_time_minutes, df, search_radius, top_k=3):
    log_user_action(
        "build_route",
        start=start_position,
        radius=search_radius,
        total_time=total_time_minutes,
    )

    rng = random.Random()

    current_position = start_position
    remaining_time = total_time_minutes
    route = []
    visited_ids = set()

    while remaining_time > 20:
        candidates = []

        for _, obj in df.iterrows():
            if obj["id"] in visited_ids:
                continue

            score, distance, visit_time = calculate_score(obj, user_categories, current_position, search_radius)
            if score == 0:
                continue
            travel_time = calculate_walking_time(distance)

            if travel_time + visit_time <= remaining_time:
                candidates.append({
                    "object": obj,
                    "score": score,
                    "distance": distance,
                    "visit_time": visit_time,
                    "travel_time": travel_time,
                })

        if not candidates:
            break

        candidates.sort(key=lambda x: x["score"], reverse=True)
        pool = candidates[: max(1, top_k)]

        chosen = rng.choice(pool)

        route.append({
            "object": chosen["object"],
            "travel_time": chosen["travel_time"],
            "visit_time": chosen["visit_time"],
            "distance": chosen["distance"],
        })

        visited_ids.add(chosen["object"]["id"])
        current_position = (chosen["object"]["lat"], chosen["object"]["lon"])
        remaining_time -= chosen["travel_time"] + chosen["visit_time"]

    return route


def generate_route_description(route):
    if not route:
        return "Маршрут не построен. Попробуйте изменить параметры."

    description = "## Ваш маршрут:\n\n"

    total_distance = 0
    total_time = 0

    for i, point in enumerate(route, 1):
        obj = point["object"]
        description += f"**{i}. {obj['title']}**\n"
        description += f"   - Время в пути: {point['travel_time']:.1f} мин\n"
        description += f"   - Время на осмотр: {point['visit_time']} мин\n"
        description += f"   - Расстояние: {point['distance']:.0f} м\n"

        short_desc = obj["description"][:200] + "..." if len(obj["description"]) > 200 else obj["description"]
        description += f"   - {short_desc}\n\n"

        total_distance += point["distance"]
        total_time += point["travel_time"] + point["visit_time"]

    description += "### Итоги:\n"
    description += f"Всего объектов: {len(route)}\n"
    description += f"Общее расстояние: {total_distance:.0f} м\n"
    description += f"Общее время: {total_time:.1f} мин\n"

    return description
