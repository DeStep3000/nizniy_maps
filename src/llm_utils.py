import os

import requests
import streamlit as st

YANDEXGPT_API_KEY = os.getenv("YANDEXGPT_API_KEY")
YANDEXGPT_FOLDER_ID = os.getenv("YANDEXGPT_FOLDER_ID")


class YandexGPTClient:
    def __init__(self):
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    # Увеличили для красочных описаний
    def generate_explanation(self, prompt, temperature=0.5, max_tokens=400):
        """Генерация текста через Yandex GPT"""
        try:

            if not YANDEXGPT_API_KEY or not YANDEXGPT_FOLDER_ID:
                return None

            headers = {
                "Authorization": f"Api-Key {YANDEXGPT_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "modelUri": f"gpt://{YANDEXGPT_FOLDER_ID}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": max_tokens
                },
                "messages": [
                    {
                        "role": "system",
                        "text": """Ты - профессиональный гид-эксперт по Нижнему Новгороду с талантом рассказчика.
                        Твоя задача - создавать красочные, увлекательные и информативные описания маршрутов.

                        СТИЛЬ ОПИСАНИЯ:
                        - Яркий, образный язык с элементами сторителлинга
                        - Подчеркивай уникальные особенности каждого объекта
                        - Показывай преимущества и ценность достопримечательностей
                        - Создавай логические связи между объектами маршрута
                        - Передавай атмосферу и исторический контекст

                        СТРУКТУРА ОТВЕТА:
                        1. Введение - общая концепция маршрута
                        2. Описание ключевых объектов с акцентом на их преимущества
                        3. Логика последовательности и практическая польза
                        4. Итог - что получит турист от этого маршрута"""
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


def generate_route_explanation(route, selected_categories, total_time, categories_dict, start_position):
    """Основная функция генерации красочного описания маршрута"""
    # Создаем клиент
    yandex_gpt = YandexGPTClient()
    if not route:
        return "Маршрут не содержит объектов."

    # Подготовка данных маршрута
    total_travel_time = sum(point["travel_time"] for point in route)
    total_visit_time = sum(point["visit_time"] for point in route)
    total_distance = sum(point["distance"] for point in route)

    selected_cats_names = [categories_dict.get(
        cat_id, "Другое") for cat_id in selected_categories]

    # Собираем детальную информацию об объектах как в первой версии
    object_descriptions = []
    for i, point in enumerate(route, 1):
        obj = point["object"]
        category_name = categories_dict.get(obj["category_id"], "Другое")

        # Полное описание объекта
        description = obj["description"]
        if len(description) > 200:  # Ограничиваем длину но оставляем информативным
            description = description[:200] + "..."

        object_info = f"{i}. {obj['title']} ({category_name}) - {description}"
        object_descriptions.append(object_info)

    descriptions_text = "\n".join(object_descriptions)

    # Создаем БОГАТЫЙ промпт с описаниями объектов
    prompt = f"""
СОЗДАЙ КРАСОЧНОЕ ОПИСАНИЕ ТУРИСТИЧЕСКОГО МАРШРУТА ПО НИЖНЕМУ НОВГОРОДУ

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
1. Раскрывает уникальные преимущества и особенности КАЖДОГО объекта
2. Объясняет, почему именно эти достопримечательности были выбраны
3. Показывает логическую связь между объектами маршрута
4. Подчеркивает практическую пользу и эмоциональную ценность прогулки
5. Создает целостный образ путешествия по Нижнему Новгороду

ОСОБЫЕ УКАЗАНИЯ:
- Используй яркие, запоминающиеся описания
- Подчеркивай историческую и культурную ценность объектов
- Покажи, как маршрут удовлетворяет интересы туриста в {", ".join(selected_cats_names)}
- Создай ощущение последовательного погружения в атмосферу города

НАЧНИ ОПИСАНИЕ:
"""

    # Генерация через Yandex GPT
    explanation = yandex_gpt.generate_explanation(prompt)

    # Если ИИ недоступен, используем улучшенный резервный вариант
    if not explanation:
        st.warning(
            "⚠️ Yandex GPT временно недоступен, используем стандартное описание")
        explanation = generate_enhanced_fallback_explanation(
            route, selected_cats_names, total_time, categories_dict, start_position, descriptions_text
        )

    return explanation


def generate_enhanced_fallback_explanation(route, selected_cats_names, total_time, categories_dict, start_position,
                                           descriptions_text=""):
    """Улучшенное резервное описание с элементами сторителлинга"""
    if not route:
        return "Маршрут не содержит объектов."

    # Анализ маршрута
    category_counts = {}
    total_distance = 0
    for point in route:
        cat_id = point["object"]["category_id"]
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        total_distance += point["distance"]

    # Основные категории
    main_categories = []
    for cat_id, count in category_counts.items():
        percentage = (count / len(route)) * 100
        cat_name = categories_dict.get(cat_id, "Другое")
        main_categories.append(f"{cat_name} ({count} объектов)")

    # Собираем ключевые объекты для упоминания
    key_objects = []
    for i, point in enumerate(route):
        # Первый, последний и средний
        if i == 0 or i == len(route) - 1 or i == len(route) // 2:
            obj = point["object"]
            key_objects.append(f"'{obj['title']}'")

    explanation = f"""Отправляйтесь в увлекательное путешествие по Нижнему Новгороду, разработанное специально для ценителей {", ".join(selected_cats_names)}!

Этот маршрут проведет вас через {len(route)} знаковых locations, начиная с {route[0]['object']['title']} и завершая {route[-1]['object']['title']}. Вы познакомитесь с богатым наследием города, где преобладают {", ".join(main_categories[:2])}.

По пути вас ждут уникальные объекты, такие как {", ".join(key_objects[:3])}, каждый из которых раскрывает свою часть истории великого города на Волге. 

Маршрут протяженностью {total_distance:.0f} метров оптимально спланирован для {total_time}-минутной прогулки, позволяя неспешно насладиться архитектурой, погрузиться в атмосферу старинных улиц и сделать памятные фотографии.

Это идеальный способ познакомиться с ключевыми достопримечательностями Нижнего Новгорода, ощутив его неповторимый характер и историческое величие."""

    return explanation
