# Поиск по документам

[![tests](https://github.com/KustovAD/testovoe/actions/workflows/tests.yml/badge.svg)](https://github.com/KustovAD/testovoe/actions/workflows/tests.yml)

Сервис полнотекстового поиска по документам. Документы хранятся в PostgreSQL, поисковый индекс — в Elasticsearch.

**Стек:** Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncpg), Elasticsearch 8, Docker Compose, pytest.

## Возможности

- поиск по тексту документа с учётом морфологии (русский и английский языки);
- выдача до 20 наиболее релевантных документов со всеми полями из БД, упорядоченных по дате создания (сначала новые);
- удаление документа по `id` из БД и индекса;
- веб-интерфейс для поиска и удаления;
- полностью асинхронная работа с БД и Elasticsearch.

## Запуск

Требуется Docker (Docker Desktop для macOS/Windows).

```bash
git clone https://github.com/KustovAD/testovoe.git
cd testovoe
make demo
```

Команда собирает и запускает сервис, PostgreSQL и Elasticsearch, после чего загружает демонстрационные данные из `data/sample.csv`.
Веб-интерфейс доступен по адресу http://localhost:8000.

### Загрузка полного набора данных

Поместите файл в `data/posts.csv` и выполните:

```bash
make up
make load
```

Формат CSV: колонки `text`, `created_date`, `rubrics` (например, `"['VK-1603736028819866', 'VK-12']"`), колонка `id` — необязательная.
Загрузка пересоздаёт таблицу и индекс.

### Без make

```bash
docker compose up -d --build
docker compose run --rm loader
```

Для загрузки демо-данных вместо `data/posts.csv`: `DATA_FILE=data/sample.csv docker compose run --rm loader`.

Остановка: `make down` (или `docker compose down`; с флагом `-v` удаляются и данные).

## API

Спецификация в формате OpenAPI — [`docs.json`](docs.json).

| Метод    | Путь                                   | Описание |
|----------|----------------------------------------|----------|
| `GET`    | `/api/v1/documents/search?query=<текст>` | Поиск документов |
| `DELETE` | `/api/v1/documents/{id}`               | Удаление документа: `204` — удалён, `404` — не найден |

Пример ответа поиска:

```json
[
  {
    "id": 12,
    "rubrics": ["VK-45"],
    "text": "Сборная выиграла товарищеский матч по футболу со счётом 2:1.",
    "created_date": "2019-11-20T22:15:03"
  }
]
```

Ошибки возвращаются в формате `{"detail": "<описание>"}`.

## Тесты

```bash
make test
```

Функциональные тесты работают с реальными PostgreSQL и Elasticsearch, используя отдельную базу `search_test` и индекс `documents_test`.
Тесты также запускаются в GitHub Actions при каждом push.

База `search_test` создаётся при первой инициализации PostgreSQL. Если volume был создан ранее, пересоздайте его: `docker compose down -v`.

## Локальный запуск без Docker

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d postgres elasticsearch
cp .env.example .env
python -m app.load_data data/sample.csv --recreate
uvicorn app.main:app --reload
pytest
```

## Конфигурация

| Переменная      | По умолчанию                                                  | Описание |
|-----------------|---------------------------------------------------------------|----------|
| `DATABASE_URL`  | `postgresql+asyncpg://postgres:postgres@localhost:5433/search` | Подключение к PostgreSQL |
| `ES_URL`        | `http://localhost:9200`                                        | Адрес Elasticsearch |
| `ES_INDEX`      | `documents`                                                    | Имя индекса |
| `SEARCH_LIMIT`  | `20`                                                           | Количество документов в выдаче |
| `POSTGRES_PORT` | `5433`                                                         | Порт PostgreSQL на хосте |
| `ES_PORT`       | `9200`                                                         | Порт Elasticsearch на хосте |
| `APP_PORT`      | `8000`                                                         | Порт сервиса на хосте |

## Устройство

- В индексе хранятся только `id` и `text`. Поиск выполняется в Elasticsearch, затем полные записи для найденных `id` запрашиваются из PostgreSQL одним запросом и сортируются по `created_date`.
- Для поля `text` настроен анализатор со стеммингом и стоп-словами для русского языка и стеммингом для английского.
- Удаление выполняется в транзакции БД: если удаление из индекса завершилось ошибкой, транзакция откатывается и данные остаются согласованными.

```
app/
  main.py        — приложение FastAPI, маршруты, обработка ошибок
  service.py     — логика поиска и удаления
  search.py      — работа с Elasticsearch
  db.py          — модель и подключение к PostgreSQL
  schemas.py     — схемы ответов
  errors.py      — сообщения об ошибках
  config.py      — настройки
  load_data.py   — загрузка CSV в БД и индекс
  static/        — веб-интерфейс
tests/           — функциональные тесты
docs.json        — спецификация OpenAPI
```
