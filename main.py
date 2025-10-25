import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import re
from datetime import datetime
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM


@st.cache_data
def load_data():
    try:
        df = pd.read_excel('cultural_objects_mnn.xlsx', sheet_name='cultural_sites_202509191434')

        def parse_coordinates(coord_str):
            if pd.isna(coord_str):
                return None, None
            matches = re.findall(r'[-+]?\d*\.\d+|\d+', str(coord_str))
            if len(matches) >= 2:
                return float(matches[1]), float(matches[0])  # lat, lon
            return None, None

        coords = df['coordinate'].apply(parse_coordinates)
        df['lat'] = coords.apply(lambda x: x[0] if x[0] is not None else None)
        df['lon'] = coords.apply(lambda x: x[1] if x[1] is not None else None)

        df = df.dropna(subset=['lat', 'lon'])

        df['description'] = df['description'].fillna('Описание отсутствует')

        return df

    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")


@st.cache_resource
def load_llm():
    """Загрузка более крупной модели для генерации текста"""
    try:
        model_name = "sberbank-ai/rugpt3small_based_on_gpt2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)

        generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=-1,
            dtype=torch.float32,
            truncation=True
        )
        return generator
    except Exception as e:
        st.error(f"Ошибка загрузки LLM: {e}")
        st.info("Используется упрощенный режим без ИИ-объяснений")
        return None


def generate_yandex_maps_url(route, start_position):
    """Генерация URL для построения маршрута в Яндекс Картах"""
    if not route:
        return None

    points = [start_position]  # Начальная точка

    for point in route:
        obj = point['object']
        points.append((obj['lat'], obj['lon']))

    points_str = []
    for i, (lat, lon) in enumerate(points):
        if i == 0:
            points_str.append(f"{lat},{lon}")  # Первая точка
        else:
            points_str.append(f"{lat},{lon}")

    route_points = "~".join(points_str)

    yandex_url = f"https://yandex.ru/maps/?rtext={route_points}&rtt=pd"

    return yandex_url


def generate_route_explanation(route, selected_categories, total_time, categories_dict, start_position):
    """Генерация объяснения маршрута с помощью более крупной LLM"""

    total_travel_time = 0
    total_visit_time = 0

    for i, point in enumerate(route):
        obj = point['object']

        total_travel_time += point['travel_time']
        total_visit_time += point['visit_time']

    object_descriptions = []
    for i, point in enumerate(route):
        obj = point['object']
        category_name = categories_dict.get(obj['category_id'], 'Другое')
        short_description = obj['description'][:100] + "..." if len(obj['description']) > 100 else obj['description']
        object_descriptions.append(f"{i + 1}. {obj['title']} ({category_name}): {short_description}")

    descriptions_text = "\n".join(object_descriptions)

    selected_cats_names = [categories_dict.get(cat_id, "Другое") for cat_id in selected_categories]

    prompt = f"""
Я создал культурный маршрут по Нижнему Новгороду для туриста. Пожалуйста, создай краткое и увлекательное объяснение этого маршрута.

Информация о маршруте:
- Начальная точка: {start_position}
- Выбранные категории интересов: {', '.join(selected_cats_names)}
- Общее время маршрута: {total_time} минут
- Количество объектов: {len(route)}
- Общее время в пути: {total_travel_time:.1f} минут
- Общее время на осмотр: {total_visit_time} минут

Объекты маршрута по порядку:
{descriptions_text}

Пожалуйста, объясни логику построения этого маршрута, почему выбраны именно эти объекты и в таком порядке, как они связаны с интересами пользователя. Сделай объяснение кратким (3-4 предложения), информативным и мотивирующим.

Объяснение:
"""

    generator = load_llm()

    if generator is None:
        return generate_enhanced_fallback_explanation(route, selected_cats_names, total_time, categories_dict,
                                                      start_position)

    try:
        response = generator(
            prompt,
            max_length=400,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=generator.tokenizer.eos_token_id,
            repetition_penalty=1.3,
            no_repeat_ngram_size=2
        )

        explanation = response[0]['generated_text']
        if explanation.startswith(prompt):
            explanation = explanation[len(prompt):].strip()

        return explanation

    except Exception as e:
        st.error(f"Ошибка генерации объяснения: {e}")
        return generate_enhanced_fallback_explanation(route, selected_cats_names, total_time, categories_dict,
                                                      start_position)


def generate_enhanced_fallback_explanation(route, selected_cats_names, total_time, categories_dict, start_position):
    """Улучшенное резервное объяснение на основе правил"""

    if not route:
        return "Маршрут не содержит объектов."

    category_counts = {}
    for point in route:
        cat_id = point['object']['category_id']
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    main_categories = []
    for cat_id, count in category_counts.items():
        cat_name = categories_dict.get(cat_id, "Другое")
        main_categories.append(f"{cat_name} ({count} объектов)")

    total_distance = sum(point['distance'] for point in route)
    avg_time_per_object = total_time / len(route) if route else 0

    explanation = f"Этот маршрут идеально соответствует вашим интересам в {', '.join(selected_cats_names)}. "
    explanation += f"За {total_time} минут вы посетите {len(route)} ключевых достопримечательностей, начиная от '{route[0]['object']['title']}' "

    if len(route) > 1:
        explanation += f"и заканчивая '{route[-1]['object']['title']}'. "

    explanation += f"Основной акцент сделан на {', '.join(main_categories)}. "
    explanation += f"Маршрут протяженностью {total_distance:.0f} метров оптимизирован для пешеходной прогулки, "
    explanation += f"с равномерным распределением времени (в среднем {avg_time_per_object:.1f} минут на объект)."

    return explanation


def calculate_distance(coord1, coord2):
    """Расчет расстояния между двумя точками в метрах"""
    return geodesic(coord1, coord2).meters


def calculate_walking_time(distance_meters):
    """Расчет времени ходьбы (пешеходная скорость ~5 км/ч)"""
    walking_speed_kmh = 5
    walking_speed_ms = walking_speed_kmh * 1000 / 3600
    time_minutes = (distance_meters / walking_speed_ms) / 60
    return max(5, time_minutes)


def calculate_score(object_data, user_categories, current_position, max_distance=2000):
    """Расчет скора для объекта"""
    if pd.isna(object_data['lat']) or pd.isna(object_data['lon']):
        return 0, 0, 0

    obj_coord = (object_data['lat'], object_data['lon'])
    distance = calculate_distance(current_position, obj_coord)

    if distance > max_distance:
        return 0, 0, 0

    category_match = 1 if object_data['category_id'] in user_categories else 0.1

    visit_time = 20

    distance_km = distance / 1000
    score = category_match / (distance_km + 0.1)

    return score, distance, visit_time


def plan_route(start_position, user_categories, total_time_minutes, df):
    """Планирование маршрута"""
    current_position = start_position
    remaining_time = total_time_minutes
    route = []
    visited_ids = set()

    while remaining_time > 20:
        best_score = 0
        best_object = None
        best_distance = 0
        best_visit_time = 0

        for _, obj in df.iterrows():
            if obj['id'] in visited_ids:
                continue

            score, distance, visit_time = calculate_score(obj, user_categories, current_position)

            travel_time = calculate_walking_time(distance)
            total_obj_time = travel_time + visit_time

            if score > best_score and total_obj_time <= remaining_time:
                best_score = score
                best_object = obj
                best_distance = distance
                best_visit_time = visit_time

        if best_object is None:
            break

        travel_time = calculate_walking_time(best_distance)
        route.append({
            'object': best_object,
            'travel_time': travel_time,
            'visit_time': best_visit_time,
            'distance': best_distance
        })

        visited_ids.add(best_object['id'])
        current_position = (best_object['lat'], best_object['lon'])
        remaining_time -= (travel_time + best_visit_time)

    return route


def generate_route_description(route):
    """Генерация описания маршрута"""
    if not route:
        return "Маршрут не построен. Попробуйте изменить параметры."

    description = "## 🗺️ Ваш маршрут:\n\n"

    total_distance = 0
    total_time = 0

    for i, point in enumerate(route, 1):
        obj = point['object']
        description += f"**{i}. {obj['title']}**\n"
        description += f"   - 🕒 Время в пути: {point['travel_time']:.1f} мин\n"
        description += f"   - ⏱️ Время на осмотр: {point['visit_time']} мин\n"
        description += f"   - 📍 Расстояние: {point['distance']:.0f} м\n"

        short_desc = obj['description'][:200] + "..." if len(obj['description']) > 200 else obj['description']
        description += f"   - ℹ️ {short_desc}\n\n"

        total_distance += point['distance']
        total_time += point['travel_time'] + point['visit_time']

    description += f"### Итоги:\n"
    description += f"📊 Всего объектов: {len(route)}\n"
    description += f"🗺️ Общее расстояние: {total_distance:.0f} м\n"
    description += f"⏱️ Общее время: {total_time:.1f} мин\n"

    return description


def create_interactive_map(df, selected_categories, center_lat, center_lon, search_radius, start_position=None,
                           route=None):
    """Создание интерактивной карты с фильтрацией по категориям"""

    filtered_df = df[df['category_id'].isin(selected_categories)] if selected_categories else df

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    if start_position:
        folium.Marker(
            start_position,
            popup="Начальная точка",
            tooltip="Начальная точка (кликните для изменения)",
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)

    if route:
        route_coords = [start_position] if start_position else []
        for point in route:
            obj = point['object']
            route_coords.append([obj['lat'], obj['lon']])

        folium.PolyLine(
            route_coords,
            color='blue',
            weight=4,
            opacity=0.7,
            popup='Маршрут прогулки'
        ).add_to(m)

    category_colors = {
        1: 'red',
        2: 'green',
        3: 'lightblue',
        4: 'blue',
        5: 'darkred',
        6: 'orange',
        7: 'purple',
        8: 'pink',
        9: 'white',
        10: 'lightgreen'
    }

    categories_dict = {
        1: "🗿 Памятники и скульптуры",
        2: "🌳 Парки и скверы",
        3: "♿ Тактильные макеты",
        4: "🏞️ Набережные",
        5: "🏗️ Архитектура",
        6: "🎭 Досуговые центры",
        7: "🏛️ Музеи",
        8: "🎪 Театры",
        9: "🌍 Города-побратимы",
        10: "🎨 Мозаики и панно"
    }

    for _, row in filtered_df.iterrows():
        if pd.isna(row['lat']) or pd.isna(row['lon']):
            continue

        color = category_colors.get(row['category_id'], 'gray')
        category_name = categories_dict.get(row['category_id'], 'Другое')

        popup_html = f"""
        <div style="width: 250px;">
            <h4>{row['title']}</h4>
            <p><b>Категория:</b> {category_name}</p>
            <p><b>Описание:</b> {row['description'][:150]}...</p>
        </div>
        """

        folium.Marker(
            [row['lat'], row['lon']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['title']} ({category_name})",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)

    if start_position:
        folium.Circle(
            location=start_position,
            radius=search_radius,
            color='blue',
            fill=True,
            fillOpacity=0.1,
            tooltip=f"Радиус поиска: {search_radius}м"
        ).add_to(m)

    return m


def main():
    st.set_page_config(page_title="Нижний Новгород - Планировщик маршрутов", layout="wide")

    st.title("🏛️ Интерактивный планировщик культурных маршрутов Нижнего Новгорода")

    if 'start_position' not in st.session_state:
        st.session_state.start_position = (56.326887, 44.005986)  # Центр НН
    if 'selected_categories' not in st.session_state:
        st.session_state.selected_categories = [1, 2, 7]
    if 'last_click' not in st.session_state:
        st.session_state.last_click = None
    if 'route_built' not in st.session_state:
        st.session_state.route_built = False
    if 'current_route' not in st.session_state:
        st.session_state.current_route = None
    if 'route_explanation' not in st.session_state:
        st.session_state.route_explanation = None

    df = load_data()

    st.sidebar.header("🎯 Настройки маршрута")

    categories = {
        1: "🗿 Памятники и скульптуры",
        2: "🌳 Парки и скверы",
        3: "♿ Тактильные макеты",
        4: "🏞️ Набережные",
        5: "🏗️ Архитектура",
        6: "🎭 Досуговые центры",
        7: "🏛️ Музеи",
        8: "🎪 Театры",
        9: "🌍 Города-побратимы",
        10: "🎨 Мозаики и панно"
    }

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

    use_llm = st.sidebar.checkbox("🤖 Использовать ИИ для объяснения маршрута", value=True)

    st.sidebar.subheader("🚀 Быстрый выбор точки старта")
    popular_points = {
        "Кремль": (56.326887, 44.005986),
        "Площадь Минина": (56.327266, 44.006597),
        "Большая Покровская": (56.318136, 43.995234),
        "Набережная Федоровского": (56.325238, 43.985295),
        "Стрелка": (56.334505, 43.976589)
    }

    selected_point = st.sidebar.selectbox("Выберите популярную точку:", list(popular_points.keys()))
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
            with st.spinner("Планируем оптимальный маршрут..."):
                route = plan_route(st.session_state.start_position, selected_categories, total_time, df)

            if route:
                st.session_state.current_route = route
                st.session_state.route_built = True

                if use_llm:
                    with st.spinner("🤖 Анализируем логику маршрута..."):
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

                st.sidebar.success(f"✅ Маршрут построен! Посещено объектов: {len(route)}")
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

            yandex_url = generate_yandex_maps_url(route, st.session_state.start_position)

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
                    st.write(f"**Категория:** {categories.get(obj['category_id'], 'Другое')}")
                    st.write(f"**Время в пути:** {point['travel_time']:.1f} мин")
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
        st.write(f"Точка старта: {st.session_state.start_position[0]:.6f}, {st.session_state.start_position[1]:.6f}")


if __name__ == "__main__":
    main()