import streamlit as st
import torch
import requests
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


@st.cache_resource(show_spinner=False)
def load_llm():
    try:
        model_name = "sberbank-ai/rugpt3small_based_on_gpt2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        generator = pipeline(
            "text-generation", model=model, tokenizer=tokenizer, device=-1, dtype=torch.float32, truncation=True
        )
        return generator
    except Exception as e:
        st.error(f"Ошибка загрузки LLM: {e}")
        st.info("Используется упрощенный режим без ИИ-объяснений")
        return None


def generate_enhanced_fallback_explanation(route, selected_categories, total_time, categories_dict):
    if not route:
        return "Маршрут не содержит объектов."

    category_counts = {}
    for point in route:
        cat_id = point["object"]["category_id"]
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1

    main_categories = []
    for cat_id, count in category_counts.items():
        print(categories_dict)
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


def generate_route_explanation(route, selected_categories, total_time, categories_dict, start_position):
    total_travel_time = 0
    total_visit_time = 0
    for point in route:
        total_travel_time += point["travel_time"]
        total_visit_time += point["visit_time"]

    object_descriptions = []
    for i, point in enumerate(route):
        obj = point["object"]
        category_name = categories_dict.get(obj["category_id"], "Другое")
        short_description = obj["description"][:100] + "..." if len(obj["description"]) > 100 else obj["description"]
        object_descriptions.append(f"{i + 1}. {obj['title']} ({category_name}): {short_description}")

    descriptions_text = "\n".join(object_descriptions)
    selected_cats_names = [categories_dict.get(cat_id, "Другое") for cat_id in selected_categories]

    prompt = f"""
Я создал культурный маршрут по Нижнему Новгороду для туриста.
Пожалуйста, создай краткое и увлекательное объяснение этого маршрута.

Информация о маршруте:
- Начальная точка: {start_position}
- Выбранные категории интересов: {", ".join(selected_cats_names)}
- Общее время маршрута: {total_time} минут
- Количество объектов: {len(route)}
- Общее время в пути: {total_travel_time:.1f} минут
- Общее время на осмотр: {total_visit_time} минут

Объекты маршрута по порядку:
{descriptions_text}

Пожалуйста, объясни логику построения этого маршрута, почему выбраны именно эти объекты и в таком порядке,
как они связаны с интересами пользователя. Сделай объяснение кратким (3-4 предложения), информативным и мотивирующим.

Объяснение:
"""
    print(prompt)

    generator = load_llm()
    if generator is None:
        return generate_enhanced_fallback_explanation(
            route, selected_cats_names, total_time, categories_dict, start_position
        )

    try:
        response = generator(
            prompt,
            max_length=400,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=generator.tokenizer.eos_token_id,
            repetition_penalty=1.3,
            no_repeat_ngram_size=2,
        )
        explanation = response[0]["generated_text"]
        if explanation.startswith(prompt):
            explanation = explanation[len(prompt) :].strip()
        return explanation
    except Exception as e:
        st.error(f"Ошибка генерации объяснения: {e}")
        return generate_enhanced_fallback_explanation(
            route, selected_cats_names, total_time, categories_dict, start_position
        )


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
