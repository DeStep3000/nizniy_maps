FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Устанавливаем uv
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir uv

# Создаём и активируем виртуальное окружение для всего образа
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем проект и файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем все зависимости через uv (использует lock-файл)
RUN uv sync --frozen

# Код приложения
COPY . /app

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
