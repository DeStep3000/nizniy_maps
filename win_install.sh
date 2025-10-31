#!/bin/bash
# Скрипт для локальной установки зависимостей проекта nizhny_maps

# 1. Создание виртуального окружения
python -m venv .venv

# 2. Активация окружения
source .venv/Scripts/activate

# 3. Установка uv
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir uv

# 4. Установка зависимостей из pyproject.toml (использует uv.lock)
uv sync

echo "Установка завершена. Активируйте окружение командой:"
echo "source .venv/Scripts/activate"