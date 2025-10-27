def generate_yandex_maps_url(route, start_position):
    if not route:
        return None

    points = [start_position]
    for point in route:
        obj = point['object']
        points.append((obj['lat'], obj['lon']))

    points_str = [f"{lat},{lon}" for (lat, lon) in points]
    route_points = "~".join(points_str)
    yandex_url = f"https://yandex.ru/maps/?rtext={route_points}&rtt=pd"
    return yandex_url
