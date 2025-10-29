import folium
import pandas as pd

from src.constants import CATEGORIES as categories
from src.constants import CATEGORY_COLORS as category_colors


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
            icon=folium.Icon(color="green", icon="play", prefix="fa"),
        ).add_to(m)

    if route:
        route_coords = [start_position] if start_position else []
        for point in route:
            obj = point["object"]
            route_coords.append([obj["lat"], obj["lon"]])

        folium.PolyLine(route_coords, color="blue", weight=4, opacity=0.7, popup="Маршрут прогулки").add_to(m)

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