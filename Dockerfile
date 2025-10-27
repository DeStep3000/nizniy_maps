FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Устанавливаем uv
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir uv

# Создаём и активируем виртуальное окружение для всего образа
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем torch CPU-only 2.9.0
RUN uv pip install "torch==2.9.0" --index-url https://download.pytorch.org/whl/cpu

# Остальные зависимости
COPY requirements.txt ./
RUN uv pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . /app

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
