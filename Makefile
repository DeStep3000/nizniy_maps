.PHONY: run dev build rebuild rebuild_dev clean view_logs go_in_docker down restart logs help

# Конфигурация
IMAGE_NAME=nizhny_maps
CONTAINER_NAME=nizhny_maps

ifeq ($(OS),Windows_NT)
	HOST_DIR := $(shell cd)
else
	HOST_DIR := $(shell pwd)
endif

# Запуск продакшн-контейнера
run:
	docker compose up -d

# 🧑Запуск в режиме разработки
dev:
	docker compose -f docker-compose.dev.yml up

# Сборка продакшн-образа
build:
	docker compose build

# Пересборка и запуск продакшн-версии
rebuild:
	docker compose build && docker compose up -d

# Пересборка и запуск dev-версии
rebuild_dev:
	docker compose build && docker compose -f docker-compose.dev.yml up

# Очистка контейнеров, образов и временных файлов
clean:
	docker rm -f $(CONTAINER_NAME) || true
	docker rmi -f $(IMAGE_NAME) || true
	docker volume prune -f || true
	docker system prune -f || true

# Остановка контейнеров
down:
	docker compose down

# Перезапуск контейнера
restart:
	docker compose restart $(CONTAINER_NAME)

# Просмотр последних логов
view_logs:
	docker logs -f --since 10s $(CONTAINER_NAME)

# Все логи docker-compose
logs:
	docker compose logs -f

# Вход в контейнер
go_in_docker:
	docker exec -it $(CONTAINER_NAME) bash

# Подсказка по командам
help:
	@echo "Доступные команды:"
	@echo "  make run           — запуск продакшн-контейнера"
	@echo "  make dev           — запуск в dev-режиме"
	@echo "  make build         — сборка образа"
	@echo "  make rebuild       — пересборка и запуск (prod)"
	@echo "  make rebuild_dev   — пересборка и запуск (dev)"
	@echo "  make down          — остановить контейнеры"
	@echo "  make restart       — перезапустить контейнер"
	@echo "  make view_logs     — последние логи контейнера"
	@echo "  make logs          — все логи docker-compose"
	@echo "  make go_in_docker  — зайти внутрь контейнера"
	@echo "  make clean         — очистка образов и контейнеров"
