import requests
import json



def generate_enhanced_fallback_explanation(route, selected_categories, total_time, categories_dict):
    if not route:
        return "Маршрут не содержит объектов."

    category_counts = {}
    for point in route:
        cat_id = point["object"]["category_id"]
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    main_categories = []
    for cat_id, count in category_counts.items():
        cat_name = categories_dict.get(cat_id, "Другое")
        main_categories.append(f"{cat_name} ({count} объектов)")

    total_distance = sum(point["distance"] for point in route)
    avg_time_per_object = total_time / len(route) if route else 0

    selected_cats_names = [categories_dict.get(cat_id, "Другое") for cat_id in selected_categories]
    explanation = f"Этот маршрут идеально соответствует вашим интересам в {', '.join(selected_cats_names)}. "
    explanation += f"За {total_time} минут вы посетите {len(route)} ключевых достопримечательностей, начиная от '{route[0]['object']['title']}' "  # noqa: E501

    if len(route) > 1:
        explanation += f"и заканчивая '{route[-1]['object']['title']}'. "

    explanation += f"Основной акцент сделан на {', '.join(main_categories)}. "
    explanation += f"Маршрут протяженностью {total_distance:.0f} метров оптимизирован для пешеходной прогулки, "
    explanation += f"с равномерным распределением времени (в среднем {avg_time_per_object:.1f} минут на объект)."

    return explanation


def generate_route_explanation_new(route, selected_categories, categories_dict):
    object_descriptions = []
    for i, point in enumerate(route):
        obj = point["object"]
        category_name = categories_dict.get(obj["category_id"], "Другое")
        short_description = obj["description"][:100] + "..." if len(obj["description"]) > 100 else obj["description"]
        object_descriptions.append(f"{i + 1}. {obj['title']} ({category_name}): {short_description}")

    descriptions_text = "\n".join(object_descriptions)
    selected_cats_names = [categories_dict.get(cat_id, "Другое") for cat_id in selected_categories]

    prompt = f"""
    Ты - культурный гид. Cоздай краткое и увлекательное объяснение построенного маршрута. Пожалуйста, объясни логику построения этого маршрута, почему выбраны именно эти объекты и в таком порядке,
    как они связаны с интересами пользователя. Сделай объяснение кратким (3-4 предложения) и объясни связь с интересами пользователя.

    - Выбранные категории интересов: {", ".join(selected_cats_names)}

    Объекты маршрута по порядку:
    {descriptions_text}
    """

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": "openai/gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                    ]
                }
            ],

        })
    )
    response_data = response.json()

    response_text = response_data['choices'][0]['message']['content']

    return response_text
