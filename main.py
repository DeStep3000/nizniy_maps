from datetime import datetime

import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from src.constants import CATEGORIES as categories
from src.data_loader import load_data
from src.llm_utils import generate_enhanced_fallback_explanation, generate_route_explanation
from src.map_utils import create_interactive_map
from src.routing import generate_route_description, plan_route
from src.utils import generate_yandex_maps_url, apply_chat_style, chat_response


def _init_state():
    if "start_position" not in st.session_state:
        st.session_state.start_position = (56.326887, 44.005986)
    if "selected_categories" not in st.session_state:
        st.session_state.selected_categories = [1, 2, 7]
    if "route_built" not in st.session_state:
        st.session_state.route_built = False
    if "current_route" not in st.session_state:
        st.session_state.current_route = None
    if "route_explanation" not in st.session_state:
        st.session_state.route_explanation = None
    if "explanation_generating" not in st.session_state:
        st.session_state.explanation_generating = False
    if "used_llm_route_explanation" not in st.session_state:
        st.session_state.used_llm_route_explanation = False
    if "getting_location" not in st.session_state:
        st.session_state.getting_location = False


def main():  # noqa: C901
    st.set_page_config(page_title="Нижний Новгород - Планировщик маршрутов", layout="wide")
    st.markdown("""
        <h1 style='
            font-size: 3.5vw;
            color: #ff6b6b;
            text-align: center;
            font-family: Arial;
        '>Интерактивный планировщик культурных маршрутов Нижнего Новгорода</h1>
    """, unsafe_allow_html=True)

    _init_state()
    df = load_data()

    st.sidebar.markdown(
        "<h2 style='color: #ff6b6b; font-size: 3vw; text-align: center; font-weight: bold;'>Настройки маршрута</h2>",
        unsafe_allow_html=True
    )

    st.sidebar.subheader("Выберите интересующие категории:")
    selected_categories = []
    col1, col2 = st.sidebar.columns(2)

    with col1:
        for cat_id, cat_name in list(categories.items())[:len(categories) // 2]:
            is_checked = cat_id in st.session_state.selected_categories
            if st.checkbox(cat_name, value=is_checked, key=f"cat_{cat_id}"):
                selected_categories.append(cat_id)

    with col2:
        for cat_id, cat_name in list(categories.items())[len(categories) // 2:]:
            is_checked = cat_id in st.session_state.selected_categories
            if st.checkbox(cat_name, value=is_checked, key=f"cat_{cat_id}_2"):
                selected_categories.append(cat_id)

    st.session_state.selected_categories = selected_categories

    total_time = st.sidebar.slider("Время на прогулку (минут):", min_value=30, max_value=240, value=120, step=15)

    search_radius = st.sidebar.slider(
        "Радиус поиска объектов (метров):", min_value=500, max_value=3000, value=1500, step=100
    )

    use_llm = st.sidebar.checkbox("🤖 Использовать ИИ для объяснения маршрута", value=True)

    st.sidebar.markdown(
        "<h2 style='color: #ff6b6b; font-size: 3vw; text-align: center; font-weight: bold;'>Выбор точки старта</h2>",
        unsafe_allow_html=True
    )
    popular_points = {
        "Кремль": (56.326887, 44.005986),
        "Площадь Минина": (56.327266, 44.006597),
        "Большая Покровская": (56.318136, 43.995234),
        "Набережная Федоровского": (56.325238, 43.985295),
        "Стрелка": (56.334505, 43.976589),
    }

    selected_point = st.sidebar.selectbox("Выберите популярную точку и нажмите кнопку ниже:", list(popular_points.keys()))
    if st.sidebar.button("Установить точку старта"):
        st.session_state.start_position = popular_points[selected_point]
        st.session_state.route_built = False
        st.session_state.route_explanation = None
        st.session_state.explanation_generating = False
        st.rerun()

    if st.session_state.getting_location:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state.start_position = (loc['coords']['latitude'], loc['coords']['longitude'])
            st.session_state.route_built = False
            st.session_state.route_explanation = None
            st.session_state.explanation_generating = False
            st.session_state.getting_location = False
            st.rerun()
        elif loc:
            st.sidebar.error("Не удалось определить координаты местоположения")
            st.session_state.getting_location = False

    st.sidebar.markdown(
        "<h2 style='color: #ff6b6b; font-size: 3vw; text-align: center; font-weight: bold;'>Использовать геолокацию</h2>",
        unsafe_allow_html=True
    )
    if st.sidebar.button("📍 Использовать мое местоположение"):
        st.session_state.getting_location = True
        st.rerun()

    if st.sidebar.button("🚀 Построить маршрут", type="primary", use_container_width=True):
        if not selected_categories:
            st.sidebar.error("Пожалуйста, выберите хотя бы одну категорию!")
        else:
            with st.spinner("Построение маршрута..."):
                route = plan_route(st.session_state.start_position, selected_categories, total_time, df, search_radius)
            if route:
                st.session_state.current_route = route
                st.session_state.route_built = True
                st.session_state.route_explanation = None
                st.session_state.explanation_generating = True
                st.sidebar.success(f"✅ Маршрут построен! Посещено объектов: {len(route)}")
                st.rerun()
            else:
                st.sidebar.warning(
                    "⚠️ Не удалось построить маршрут. Попробуйте увеличить время или изменить начальную точку."
                )

    if st.session_state.route_built:
        if st.sidebar.button("🗑️ Сбросить маршрут", type="secondary"):
            st.session_state.route_built = False
            st.session_state.current_route = None
            st.session_state.route_explanation = None
            st.session_state.explanation_generating = False
            st.rerun()

    if not st.session_state.route_built:
        st.subheader("🗺️ Интерактивная карта достопримечательностей")
        st.markdown(
            "**💡 Подсказка:** Кликните один раз на карте, чтобы установить собственную точку старта. Выбранные категории отображаются сразу."
        )

        with st.spinner("Загружаем карту..."):
            map_obj = create_interactive_map(
                df,
                selected_categories,
                st.session_state.start_position[0],
                st.session_state.start_position[1],
                search_radius,
                st.session_state.start_position,
                None,
            )

            map_data = st_folium(map_obj, width=None, height=600, returned_objects=["last_clicked"])

            if map_data and map_data.get("last_clicked"):
                clicked_lat = map_data["last_clicked"]["lat"]
                clicked_lon = map_data["last_clicked"]["lng"]

                if (clicked_lat, clicked_lon) != st.session_state.start_position:
                    st.session_state.start_position = (clicked_lat, clicked_lon)
                    st.session_state.route_built = False
                    st.session_state.route_explanation = None
                    st.session_state.explanation_generating = False
                    st.rerun()
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("🗺️ Интерактивная карта достопримечательностей")
            st.markdown(
                "**💡 Подсказка:** Кликните один раз на карте, чтобы установить собственную точку старта. Выбранные категории отображаются сразу."
            )

            with st.spinner("Строим маршрут..."):
                map_obj = create_interactive_map(
                    df,
                    selected_categories,
                    st.session_state.start_position[0],
                    st.session_state.start_position[1],
                    search_radius,
                    st.session_state.start_position,
                    st.session_state.current_route
                )

                map_data = st_folium(map_obj, width=None, height=500, returned_objects=["last_clicked"])

                if map_data and map_data.get("last_clicked"):
                    clicked_lat = map_data["last_clicked"]["lat"]
                    clicked_lon = map_data["last_clicked"]["lng"]

                    if (clicked_lat, clicked_lon) != st.session_state.start_position:
                        st.session_state.start_position = (clicked_lat, clicked_lon)
                        st.session_state.route_built = False
                        st.session_state.route_explanation = None
                        st.session_state.explanation_generating = False
                        st.rerun()

            if (use_llm and
                    st.session_state.explanation_generating and
                    st.session_state.route_explanation is None):
                with st.spinner("🎨 Создаем красочное описание маршрута с ИИ..."):
                    explanation = generate_route_explanation(
                        st.session_state.current_route,
                        selected_categories,
                        total_time,
                        categories,
                        st.session_state.start_position
                    )
                    st.session_state.route_explanation = explanation
                    st.session_state.explanation_generating = False
                    st.session_state.used_llm_route_explanation = True
                    st.rerun()
            elif (st.session_state.explanation_generating and
                    st.session_state.route_explanation is None):
                with st.spinner("❓ Создаем объяснение маршрута..."):
                    explanation = generate_enhanced_fallback_explanation(
                            st.session_state.current_route,
                            selected_categories,
                            total_time,
                            categories,
                            st.session_state.start_position)
                    st.session_state.route_explanation = explanation
                    st.session_state.explanation_generating = False
                    st.session_state.used_llm_route_explanation = False
                    st.rerun()

            if st.session_state.route_explanation:
                apply_chat_style()
                chat_response(st.session_state.route_explanation, st.session_state.used_llm_route_explanation)

        with col2:
            if st.session_state.current_route:
                route = st.session_state.current_route

                yandex_url = generate_yandex_maps_url(route, st.session_state.start_position)

                st.subheader("📍 Построенный маршрут")

                if yandex_url:
                    st.markdown(
                        f'<a href="{yandex_url}" target="_blank"><button style="background-color: #FF0000; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%;">🗺️ Открыть маршрут в Яндекс Картах</button></a>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                st.subheader("📝 Детали маршрута")

                total_distance = 0
                total_time_route = 0

                for i, point in enumerate(route, 1):
                    obj = point["object"]

                    with st.expander(f"{i}. {obj['title']}", expanded=(i == 1)):
                        st.write(f"**Категория:** {categories.get(obj['category_id'], 'Другое')}")
                        st.write(f"**Время в пути:** {point['travel_time']:.1f} мин")
                        st.write(f"**Время на осмотр:** {point['visit_time']} мин")
                        st.write(f"**Расстояние:** {point['distance']:.0f} м")
                        st.write(f"**Описание:** {obj['description']}")

                        st.code(f"Координаты: {obj['lat']:.6f}, {obj['lon']:.6f}")

                    total_distance += point["distance"]
                    total_time_route += point["travel_time"] + point["visit_time"]

                st.subheader("📊 Итоги маршрута")
                col_stat1, col_stat2, col_stat3 = st.columns(3)

                with col_stat1:
                    st.metric("Объектов", len(route))
                with col_stat2:
                    st.metric("Общее расстояние", f"{total_distance:.0f} м")
                with col_stat3:
                    st.metric("Общее время", f"{total_time_route:.1f} мин")

                description = generate_route_description(route)
                st.download_button(
                    label="📥 Скачать описание маршрута",
                    data=description,
                    file_name=f"маршрут_нижний_новгород_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()