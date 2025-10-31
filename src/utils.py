import streamlit as st

def generate_yandex_maps_url(route, start_position):
    if not route:
        return None

    points = [start_position]
    for point in route:
        obj = point["object"]
        points.append((obj["lat"], obj["lon"]))

    points_str = [f"{lat},{lon}" for (lat, lon) in points]
    route_points = "~".join(points_str)
    yandex_url = f"https://yandex.ru/maps/?rtext={route_points}&rtt=pd"
    return yandex_url


def apply_chat_style():
    st.markdown("""
                <style>
                    /* Стиль для сообщений ассистента */
                    .assistant-message {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                        border: 1px solid #e0e0e0;
                        position: relative;
                        max-width: 80%;
                        margin-left: 0;
                    }

                    /* Иконка ассистента */
                    .assistant-icon {
                        position: absolute;
                        top: 15px;
                        left: 15px;
                        font-size: 20px;
                    }

                    /* Текст сообщения ассистента */
                    .assistant-text {
                        margin-left: 35px;
                        line-height: 1.6;
                    }

                    /* Заголовок в сообщениях ассистента */
                    .message-title {
                        font-weight: bold;
                        font-size: 1.1em;
                        margin-bottom: 8px;
                        color: #fff;
                    }

                    /* Контейнер чата */
                    .chat-container {
                        max-height: 600px;
                        overflow-y: auto;
                        padding: 20px;
                        background: #f8f9fa;
                        border-radius: 15px;
                        border: 1px solid #e0e0e0;
                    }
                </style>
                """, unsafe_allow_html=True)


def chat_response(response, use_llm):
    if use_llm:
        st.markdown(f"""
                    <div class="assistant-message">
                        <div class="assistant-icon">🤖</div>
                        <div class="assistant-text">
                            <div class="message-title">Туристический помощник:</div>
                            {response}
                            <br><br>
                            <strong>⚠️ *Ответ сгенерирован нейросетью и может содержать неточности. Рекомендуем проверять актуальность информации.*</strong>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
                    <div class="assistant-message">
                        <div class="assistant-icon">❓</div>
                        <div class="assistant-text">
                            <div class="message-title">Объяснение маршрута:</div>
                            {response}
                            <br><br>
                            <strong>💡 Данный ответ создан автоматически без использования AI</strong>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
