from datetime import datetime

import streamlit as st
from streamlit_folium import st_folium

from app.constants import CATEGORIES as categories
from app.data_loader import load_data
from app.llm_utils import generate_route_explanation
from app.map_utils import create_interactive_map
from app.routing import generate_route_description, plan_route
from app.utils import generate_yandex_maps_url


def _init_state():
    if 'start_position' not in st.session_state:
        st.session_state.start_position = (56.326887, 44.005986)
    if 'selected_categories' not in st.session_state:
        st.session_state.selected_categories = [1, 2, 7]
    if 'route_built' not in st.session_state:
        st.session_state.route_built = False
    if 'current_route' not in st.session_state:
        st.session_state.current_route = None
    if 'route_explanation' not in st.session_state:
        st.session_state.route_explanation = None


def main():
    st.set_page_config(
        page_title="Нижний Новгород - Планировщик маршрутов", layout="wide")
    st.title("🏛️ Интерактивный планировщик культурных маршрутов Нижнего Новгорода")

    _init_state()
    df = load_data()

    st.sidebar.header("🎯 Настройки маршрута")

    selected_categories = st.sidebar.multiselect(
        "Выберите интересующие категории:",
        options=list(categories.keys()),
        format_func=lambda x: categories[x],
        default=st.session_state.selected_categories
    )
    st.session_state.selected_categories = selected_categories

    total_time = st.sidebar.slider(
        "Время на прогулку (минут):",
        min_value=30,
        max_value=240,
        value=120,
        step=15
    )

    search_radius = st.sidebar.slider(
        "Радиус поиска объектов (метров):",
        min_value=500,
        max_value=3000,
        value=1500,
        step=100
    )

    use_llm = st.sidebar.checkbox(
        "🤖 Использовать ИИ для объяснения маршрута", value=True)

    st.sidebar.subheader("🚀 Быстрый выбор точки старта")
    popular_points = {
        "Кремль": (56.326887, 44.005986),
        "Площадь Минина": (56.327266, 44.006597),
        "Большая Покровская": (56.318136, 43.995234),
        "Набережная Федоровского": (56.325238, 43.985295),
        "Стрелка": (56.334505, 43.976589)
    }

    selected_point = st.sidebar.selectbox(
        "Выберите популярную точку:", list(popular_points.keys()))
    if st.sidebar.button("Установить точку старта"):
        st.session_state.start_position = popular_points[selected_point]
        st.session_state.route_built = False
        st.rerun()

    st.sidebar.info(
        f"📍 Текущая точка старта:\n{st.session_state.start_position[0]:.6f}, {st.session_state.start_position[1]:.6f}")
    st.sidebar.info(f"🎯 Выбрано категорий: {len(selected_categories)}")
    st.sidebar.info(
        f"📊 Всего объектов на карте: {len(df[df['category_id'].isin(selected_categories)]) if selected_categories else len(df)}")

    if st.sidebar.button("🚀 Построить маршрут", type="primary", use_container_width=True):
        if not selected_categories:
            st.sidebar.error("Пожалуйста, выберите хотя бы одну категорию!")
        else:
            # Спиннеры в UI можно оставить (по желанию),
            # но спиннер при хэшировании кэша/ресурсов отключён в декораторах cache_*.
            route = plan_route(st.session_state.start_position,
                               selected_categories, total_time, df)

            if route:
                st.session_state.current_route = route
                st.session_state.route_built = True

                if use_llm:
                    explanation = generate_route_explanation(
                        route,
                        selected_categories,
                        total_time,
                        categories,
                        st.session_state.start_position
                    )
                    st.session_state.route_explanation = explanation
                else:
                    st.session_state.route_explanation = None

                st.sidebar.success(
                    f"✅ Маршрут построен! Посещено объектов: {len(route)}")
            else:
                st.sidebar.warning(
                    "⚠️ Не удалось построить маршрут. Попробуйте увеличить время или изменить начальную точку.")

    if st.session_state.route_built:
        if st.sidebar.button("🗑️ Сбросить маршрут", type="secondary"):
            st.session_state.route_built = False
            st.session_state.current_route = None
            st.session_state.route_explanation = None
            st.rerun()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🗺️ Интерактивная карта достопримечательностей")
        st.markdown(
            "**💡 Инструкция:** Кликните на карте, чтобы установить точку старта. Выбранные категории отображаются сразу.")

        map_obj = create_interactive_map(
            df,
            selected_categories,
            st.session_state.start_position[0],
            st.session_state.start_position[1],
            search_radius,
            st.session_state.start_position,
            st.session_state.current_route if st.session_state.route_built else None
        )

        map_data = st_folium(
            map_obj,
            width=700,
            height=500,
            returned_objects=["last_clicked"]
        )

        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]

            if (clicked_lat, clicked_lon) != st.session_state.start_position:
                st.session_state.start_position = (clicked_lat, clicked_lon)
                st.session_state.route_built = False
                st.rerun()

        if st.session_state.route_built and st.session_state.route_explanation:
            st.subheader("🤖 Объяснение выбора маршрута")
            st.info(st.session_state.route_explanation)

    with col2:
        st.subheader("⚡ Быстрые действия")

        if st.session_state.route_built and st.session_state.current_route:
            route = st.session_state.current_route

            yandex_url = generate_yandex_maps_url(
                route, st.session_state.start_position)

            st.subheader("📍 Построенный маршрут")

            if yandex_url:
                st.markdown(
                    f'<a href="{yandex_url}" target="_blank"><button style="background-color: #FF0000; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%;">🗺️ Открыть маршрут в Яндекс Картах</button></a>',
                    unsafe_allow_html=True)
                st.markdown("")

            st.subheader("📝 Детали маршрута")

            total_distance = 0
            total_time_route = 0

            for i, point in enumerate(route, 1):
                obj = point['object']

                with st.expander(f"{i}. {obj['title']}", expanded=(i == 1)):
                    st.write(
                        f"**Категория:** {categories.get(obj['category_id'], 'Другое')}")
                    st.write(
                        f"**Время в пути:** {point['travel_time']:.1f} мин")
                    st.write(f"**Время на осмотр:** {point['visit_time']} мин")
                    st.write(f"**Расстояние:** {point['distance']:.0f} м")
                    st.write(f"**Описание:** {obj['description']}")

                    st.code(f"Координаты: {obj['lat']:.6f}, {obj['lon']:.6f}")

                total_distance += point['distance']
                total_time_route += point['travel_time'] + point['visit_time']

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
                use_container_width=True
            )
        else:
            st.info("👆 Настройте параметры и нажмите 'Построить маршрут' в сайдбаре")

        st.subheader("🎯 Выбранные категории")
        if selected_categories:
            for cat_id in selected_categories:
                cat_name = categories.get(cat_id, f"Категория {cat_id}")
                count = len(df[df['category_id'] == cat_id])
                st.write(f"- {cat_name} ({count} объектов)")
        else:
            st.write("Категории не выбраны")

        st.subheader("📊 Статистика")
        st.write(f"Всего объектов в базе: {len(df)}")
        st.write(
            f"Объектов на карте: {len(df[df['category_id'].isin(selected_categories)]) if selected_categories else len(df)}")
        st.write(
            f"Точка старта: {st.session_state.start_position[0]:.6f}, {st.session_state.start_position[1]:.6f}")


if __name__ == "__main__":
    main()
