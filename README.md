# FastAPI: реализуем приложение вместе

Главный учебный файл — `app.py`. В нём оставлены четыре небольших задания.
`app_final.py` — готовый вариант для преподавателя и проверки.

## Подготовка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Запуск

```bash
python -m uvicorn app:app --reload
```

После запуска:

- приложение: http://127.0.0.1:8000
- документация: http://127.0.0.1:8000/docs

## Проверка по мере реализации

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/hello?name=Anna"
```

Перед последним шагом задайте настройки и перезапустите сервер:

```bash
export APP_NAME="Проект группы 1"
export APP_AUTHOR="Иван Иванов"
python -m uvicorn app:app --reload
```

Проверка:

```bash
curl http://127.0.0.1:8000/info
```

## Если нужно быстро восстановить правильный вариант

```bash
cp app_final.py app.py
```

Промежуточные работающие версии находятся в папке `examples`.

