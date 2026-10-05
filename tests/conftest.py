import os
from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import insert

from app.config import Settings
from app.db import Document, create_tables
from app.main import create_app

BASE_DATE = datetime(2020, 1, 1, 12, 0, 0)

SEED = [
    {"id": 1, "rubrics": ["VK-1", "VK-2"], "text": "Кошки гуляли по крыше всю ночь", "created_date": BASE_DATE},
    {"id": 2, "rubrics": ["VK-3"], "text": "Собака охраняет дом", "created_date": BASE_DATE + timedelta(days=2)},
    {"id": 3, "rubrics": [], "text": "Моя кошка любит рыбу", "created_date": BASE_DATE + timedelta(days=1)},
    {"id": 4, "rubrics": ["VK-4"], "text": "Погода в Москве солнечная", "created_date": BASE_DATE + timedelta(days=3)},
] + [
    {"id": 100 + i, "rubrics": ["BULK"], "text": f"Новости футбола номер {i}",
     "created_date": BASE_DATE + timedelta(hours=i)}
    for i in range(25)
]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/search_test"
        ),
        es_url=os.getenv("TEST_ES_URL", os.getenv("ES_URL", "http://localhost:9200")),
        es_index=os.getenv("TEST_ES_INDEX", "documents_test"),
    )


@pytest.fixture
async def app(settings):
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        await create_tables(app.state.engine, drop=True)
        await app.state.index.ensure_index(recreate=True)
        async with app.state.engine.begin() as conn:
            await conn.execute(insert(Document), SEED)
        await app.state.index.index_documents(((d["id"], d["text"]) for d in SEED), refresh=True)
        yield app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
