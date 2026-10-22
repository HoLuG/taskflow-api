"""Учебная заготовка: этот файл заполняем вместе на занятии."""

from fastapi import FastAPI
from dotenv import load_dotenv

app = FastAPI(title="Наш первый сервис")

load_dotenv()

# Шаг 1. Добавьте обработчик адреса /
# Подсказка:
# @app.get("/")
# def root():
#     return {"message": "Сервис работает"}


# Шаг 2. Добавьте техническую проверку /health
# Она должна возвращать: {"status": "ok"}


# Шаг 3. Добавьте /hello с параметром name
# Пример запроса: /hello?name=Anna
# Пример ответа: {"message": "Привет, Anna!"}


# Шаг 4. Прочитайте APP_NAME и APP_AUTHOR из переменных окружения
# и верните их по адресу /info.

