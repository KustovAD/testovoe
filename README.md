# search-service

[![tests](https://github.com/KustovAD/testovoe/actions/workflows/tests.yml/badge.svg)](https://github.com/KustovAD/testovoe/actions/workflows/tests.yml)

Простой поисковик по текстам документов: FastAPI + PostgreSQL + Elasticsearch, всё асинхронно, запускается в Docker.

## Быстрый старт

Нужен только Docker. В репозитории есть небольшой демо-датасет `data/sample.csv`:

```bash
git clone https://github.com/KustovAD/testovoe.git
cd testovoe
make demo
```

После этого:

```bash
curl "http://localhost:8000/api/v1/documents/search?query=кот"
```

или открыть http://localhost:8000 в браузере.

```json
[
  {
    "id": 10,
    "rubrics": ["VK-1603736028819866"],
    "text": "Кот соседа каждое утро сидит у нас на балконе и ждёт завтрак.",
    "created_date": "2020-02-18T08:05:17"
  },
  {
    "id": 4,
    "rubrics": ["VK-1603736028819866", "VK-77"],
    "text": "Котята ищут дом! Три кошечки и один кот, приучены к лотку.",
    "created_date": "2020-01-10T14:03:55"
  }
]
```

Веб-интерфейс для поиска: http://localhost:8000. Спецификация API в формате OpenAPI — `docs.json`.

## Полный датасет

Положить файл в `data/posts.csv` (колонки `text, created_date, rubrics`) и выполнить:

```bash
make up
make load
```

Без make: `docker compose up -d --build && docker compose run --rm loader`.

## API

- `GET /api/v1/documents/search?query=<текст>` — до 20 документов, найденных в индексе, отсортированы по `created_date` (сначала новые)
- `DELETE /api/v1/documents/{id}` — удаляет документ из базы и индекса (204 / 404)

## Тесты

```bash
make test   # или docker compose run --rm tests
```

Тесты функциональные — ходят в настоящие Postgres и Elasticsearch. В CI они же гоняются через GitHub Actions.

Тесты используют отдельную базу `search_test` и индекс `documents_test`. База создаётся
init-скриптом при первом старте postgres, так что если volume уже был — `docker compose down -v`.

## Без докера

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d postgres elasticsearch
cp .env.example .env
python -m app.load_data data/posts.csv --recreate
uvicorn app.main:app --reload
```

## Порты

Наружу публикуются Postgres на `5433`, Elasticsearch на `9200` и сервис на `8000`.
Если какой-то порт занят, его можно переопределить: `POSTGRES_PORT=15432 ES_PORT=19200 APP_PORT=8080 make demo`.

## Заметки

- В индексе только `id` и `text`, остальное берётся из базы одним запросом по найденным id.
- Для текста настроен анализатор со стеммингом (ru + en), поэтому «кошкам» находит «кошка».
- При удалении документ сначала удаляется из базы в транзакции, потом из ES; если ES упал — транзакция откатывается.
