import os

import requests
import streamlit as st


class YandexGPTClient:
    """
    Клиент для работы с Yandex GPT API.
    Обеспечивает генерацию текстовых описаний через нейросеть.
    """

    def __init__(self):
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def generate_explanation(self, prompt, temperature=0.5, max_tokens=400):
        """
        Генерирует текстовое описание через Yandex GPT API.

        Args:
            prompt (str): Текст запроса для нейросети
            temperature (float): Параметр креативности (0-1)
            max_tokens (int): Максимальное количество токенов в ответе

        Returns:
            str: Сгенерированный текст или None при ошибке
        """
        try:
            # Получение учетных данных из секретов Streamlit
            api_key = os.getenv("YANDEXGPT_API_KEY")
            folder_id = os.getenv("YANDEXGPT_FOLDER_ID")

            if not api_key or not folder_id:
                return None

            headers = {
                "Authorization": f"Api-Key {api_key}",
                "Content-Type": "application/json"
            }

            # Формирование запроса к API
            payload = {
                "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": max_tokens
                },
                "messages": [
                    {
                        "role": "system",
                        "text": """Ты - профессиональный гид-эксперт по Нижнему Новгороду с талантом рассказчика.
                        Твоя задача - создавать красочные, увлекательные и информативные описания маршрутов."""
                    },
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }

            response = requests.post(
                self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result["result"]["alternatives"][0]["message"]["text"]

        except Exception as e:
            st.error(f"❌ Ошибка Yandex GPT: {e}")
            return None


# Глобальный экземпляр клиента для повторного использования
yandex_gpt = YandexGPTClient()


def generate_route_explanation(route, selected_categories, total_time, categories_dict, start_position):
    """
    Генерирует текстовое описание маршрута с использованием нейросети.

    Args:
        route (list): Список точек маршрута
        selected_categories (list): Выбранные категории интересов
        total_time (int): Общее время маршрута в минутах
        categories_dict (dict): Словарь категорий
        start_position (tuple): Координаты начальной точки

    Returns:
        str: Описание маршрута с предупреждением о возможных неточностях
    """
    if not route:
        return "Маршрут не содержит объектов."

    # Расчет общих показателей маршрута
    total_travel_time = sum(point["travel_time"] for point in route)
    total_visit_time = sum(point["visit_time"] for point in route)
    total_distance = sum(point["distance"] for point in route)

    selected_cats_names = [categories_dict.get(
        cat_id, "Другое") for cat_id in selected_categories]

    # Формирование детальных описаний каждого объекта маршрута
    object_descriptions = []
    for i, point in enumerate(route, 1):
        obj = point["object"]
        category_name = categories_dict.get(obj["category_id"], "Другое")
        description = obj["description"]

        # Обрезка длинных описаний для оптимизации промпта
        if len(description) > 200:
            description = description[:200] + "..."

        object_info = f"{i}. {obj['title']} ({category_name}) - {description}"
        object_descriptions.append(object_info)

    descriptions_text = "\n".join(object_descriptions)

    # Формирование промпта для нейросети
    prompt = f"""
СОЗДАЙ КРАСОВОЕ ОПИСАНИЕ ТУРИСТИЧЕСКОГО МАРШРУТА ПО НИЖНЕМУ НОВГОРОДУ

    ИНФОРМАЦИЯ О МАРШРУТЕ:
    - Интересы туриста: {", ".join(selected_cats_names)}
    - Общее время: {total_time} минут
    - Протяженность: {total_distance:.0f} метров
    - Количество объектов: {len(route)}
    - Время в пути: {total_travel_time:.1f} минут
    - Время на осмотр: {total_visit_time} минут

    ПОДРОБНОЕ ОПИСАНИЕ ОБЪЕКТОВ МАРШРУТА:
    {descriptions_text}

    ЗАДАЧА:
    Создай увлекательное описание этого маршрута, которое:
    1. Кратко раскрывает ключевые особенности КАЖДОГО объекта КРАТКО (1 предложение на объект)
    2. Объясняет, почему именно эти достопримечательности были выбраны
    3. Показывает логическую связь между объектами маршрута
    4. Подчеркивает практическую пользу и эмоциональную ценность прогулки
    5. Создает целостный образ путешествия по Нижнему Новгороду

    ОСОБЫЕ УКАЗАНИЯ:
    - Используй яркие, но лаконичные описания
    - Для каждого объекта выдели только САМОЕ ГЛАВНОЕ (1 ключевая особенность)
    - Подчеркивай историческую и культурную ценность объектов кратко
    - Покажи, как маршрут удовлетворяет интересы туриста в {", ".join(selected_cats_names)}
    - Создай ощущение последовательного погружения в атмосферу города
    - ОПИСАНИЕ КАЖДОГО ОБЪЕКТА ДОЛЖНО БЫТЬ КРАТКИМ И СОДЕРЖАТЕЛЬНЫМ

    НАЧНИ ОПИСАНИЕ:
"""

    # Основная генерация через нейросеть
    explanation = yandex_gpt.generate_explanation(prompt)

    # Резервный вариант при недоступности нейросети
    if not explanation:
        st.warning(
            "⚠️ Yandex GPT временно недоступен, используем стандартное описание")
        explanation = generate_enhanced_fallback_explanation(
            route, selected_cats_names, total_time, categories_dict, start_position, descriptions_text
        )

    return explanation


def generate_enhanced_fallback_explanation(route, selected_cats_names, total_time, categories_dict, start_position,
                                           descriptions_text=""):
    """
    Создает резервное описание маршрута без использования нейросети.
    Используется при недоступности Yandex GPT API.

    Args:
        route (list): Список точек маршрута
        selected_cats_names (list): Названия выбранных категорий
        total_time (int): Общее время маршрута
        categories_dict (dict): Словарь категорий
        start_position (tuple): Координаты начальной точки
        descriptions_text (str): Текстовое описание объектов

    Returns:
        str: Детальное текстовое описание маршрута
    """
    if not route:
        return "Маршрут не содержит объектов."

    if selected_cats_names and isinstance(selected_cats_names[0], int):
        selected_cats_names = [
            str(categories_dict.get(cat_id, cat_id)) for cat_id in selected_cats_names
        ]

    # Анализ распределения категорий в маршруте
    category_counts = {}
    total_distance = 0
    for point in route:
        cat_id = point["object"]["category_id"]
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        total_distance += point["distance"]

    # Определение основных категорий для упоминания в описании
    main_categories = []
    for cat_id, count in category_counts.items():
        cat_name = categories_dict.get(cat_id, "Другое")
        main_categories.append(f"{cat_name} ({count} объектов)")

    # Выбор ключевых объектов для акцента в описании
    key_objects = []
    for i, point in enumerate(route):
        # Выбираем первый, последний и средний объекты как наиболее значимые
        if i == 0 or i == len(route) - 1 or i == len(route) // 2:
            obj = point["object"]
            key_objects.append(f"'{obj['title']}'")

    # Формирование итогового описания
    explanation = f"""Отправляйтесь в увлекательное путешествие по Нижнему Новгороду, разработанное специально для ценителей {", ".join(selected_cats_names)}!

Этот маршрут проведет вас через {len(route)} знаковых локаций, начиная с {route[0]['object']['title']} и завершая {route[-1]['object']['title']}. Вы познакомитесь с богатым наследием города, где преобладают {", ".join(main_categories[:2])}.

По пути вас ждут уникальные объекты, такие как {", ".join(key_objects[:3])}, каждый из которых раскрывает свою часть истории великого города на Волге. 

Маршрут протяженностью {total_distance:.0f} метров оптимально спланирован для {total_time}-минутной прогулки, позволяя неспешно насладиться архитектурой, погрузиться в атмосферу старинных улиц и сделать памятные фотографии.

Это идеальный способ познакомиться с ключевыми достопримечательностями Нижнего Новгорода, ощутив его неповторимый характер и историческое величие."""

    return explanation
