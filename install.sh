#!/bin/bash
# Скрипт для локальной установки зависимостей проекта nizhny_maps

# 1. Создание виртуального окружения
python3 -m venv .venv

# 2. Активация окружения
source .venv/bin/activate

# 3. Установка uv 
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir uv

# 4. Установка PyTorch CPU-only
uv pip install "torch==2.9.0" --index-url https://download.pytorch.org/whl/cpu

# 5. Установка остальных зависимостей
uv pip install --no-cache-dir -r requirements.txt

echo "Установка завершена. Активируйте окружение командой:"
echo "source .venv/bin/activate"