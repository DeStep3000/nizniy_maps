import folium
import pandas as pd
import requests
from folium.features import DivIcon
from functools import lru_cache

from src.constants import CATEGORIES as categories
from src.constants import CATEGORY_COLORS as category_colors

@lru_cache(maxsize=512)
def _fetch_osrm_route(a, b):
    profile = 'foot'
    base = "https://router.project-osrm.org/route/v1"
    url = f"{base}/{profile}/{a[1]},{a[0]};{b[1]},{b[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        coords = data["routes"][0]["geometry"]["coordinates"]
        return [(lat, lon) for lon, lat in coords]
    except Exception as e:
        print(f"OSRM route fetch failed: {e}")
        return []


def create_interactive_map(
    df, selected_categories, center_lat, center_lon, search_radius, start_position=None, route=None
):
    filtered_df = df[df["category_id"].isin(selected_categories)] if selected_categories else df

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, attribution_control=False)

    if start_position:
        folium.Marker(
            start_position,
            popup="Начальная точка",
            tooltip="Начальная точка (кликните для изменения)",
            icon=folium.Icon(color="darkblue", icon="home", prefix="fa"),
        ).add_to(m)

    route_index_map = {}
    if route:
        path_coords = []
        prev = start_position if start_position else (route[0]["object"]["lat"], route[0]["object"]["lon"])

        for idx, point in enumerate(route, start=1):
            obj = point["object"]
            route_index_map[obj["id"]] = idx
            nxt = (obj["lat"], obj["lon"])
            try:
                seg = _fetch_osrm_route(prev, nxt)
                if path_coords and seg:
                    path_coords.extend(seg[1:])
                else:
                    path_coords.extend(seg)
            except Exception:
                path_coords.extend([prev, nxt])
            prev = nxt

        if path_coords:
            folium.PolyLine(
                path_coords,
                color="#9b59b6",
                weight=5,
                opacity=0.8,
                popup="Пешеходный маршрут",
            ).add_to(m)

    for _, row in filtered_df.iterrows():
        if pd.isna(row["lat"]) or pd.isna(row["lon"]):
            continue

        color = category_colors.get(row["category_id"], "gray")
        category_name = categories.get(row["category_id"], "Другое")

        popup_html = f"""
        <div style="width: 250px;">
            <h4>{row["title"]}</h4>
            <p><b>Категория:</b> {category_name}</p>
            <p><b>Описание:</b> {row["description"][:150]}...</p>
        </div>
        """

        if row["id"] in route_index_map:
            idx = route_index_map[row["id"]]
            folium.Marker(
                [row["lat"], row["lon"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{idx}. {row['title']} ({category_name})",
                icon=DivIcon(
                    icon_size=(28, 28),
                    icon_anchor=(14, 14),
                    html=f'''
                        <div style="
                            width:28px;height:28px;border-radius:50%;
                            background:#2c3e50;color:#fff;display:flex;
                            align-items:center;justify-content:center;
                            font-weight:700;font-size:14px;border:2px solid #fff;
                            box-shadow:0 1px 4px rgba(0,0,0,0.35);
                        ">{idx}</div>
                    ''',
                ),
            ).add_to(m)
        else:
            folium.Marker(
                [row["lat"], row["lon"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['title']} ({category_name})",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(m)

    if start_position:
        folium.Circle(
            location=start_position,
            radius=search_radius,
            color="blue",
            fill=True,
            fillOpacity=0.1,
            tooltip=f"Радиус поиска: {search_radius}м",
        ).add_to(m)

    return m