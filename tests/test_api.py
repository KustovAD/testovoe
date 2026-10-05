from datetime import datetime

from sqlalchemy import select

from app.db import Document

SEARCH = "/api/v1/documents/search"


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_search_returns_all_db_fields(client):
    resp = await client.get(SEARCH, params={"query": "собака"})
    assert resp.status_code == 200
    assert resp.json() == [
        {"id": 2, "rubrics": ["VK-3"], "text": "Собака охраняет дом", "created_date": "2020-01-03T12:00:00"}
    ]


async def test_search_uses_morphology_and_sorts_by_date_desc(client):
    resp = await client.get(SEARCH, params={"query": "кошкам"})
    assert resp.status_code == 200
    assert [d["id"] for d in resp.json()] == [3, 1]


async def test_search_limit_20_sorted_by_date(client):
    resp = await client.get(SEARCH, params={"query": "футбол"})
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 20
    dates = [datetime.fromisoformat(d["created_date"]) for d in docs]
    assert dates == sorted(dates, reverse=True)


async def test_search_no_results(client):
    resp = await client.get(SEARCH, params={"query": "квантовый компьютер"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_validation(client):
    assert (await client.get(SEARCH)).status_code == 422
    assert (await client.get(SEARCH, params={"query": ""})).status_code == 422
    assert (await client.get(SEARCH, params={"query": "   "})).status_code == 422


async def test_delete_removes_from_db_and_index(client, app):
    resp = await client.delete("/api/v1/documents/2")
    assert resp.status_code == 204

    async with app.state.service.sessionmaker() as session:
        assert await session.scalar(select(Document).where(Document.id == 2)) is None
    assert await app.state.index.search_ids("собака", 20) == []
    assert (await client.get(SEARCH, params={"query": "собака"})).json() == []


async def test_delete_missing_returns_404(client):
    assert (await client.delete("/api/v1/documents/999999")).status_code == 404
    assert (await client.delete("/api/v1/documents/2")).status_code == 204
    assert (await client.delete("/api/v1/documents/2")).status_code == 404


async def test_delete_invalid_id(client):
    assert (await client.delete("/api/v1/documents/abc")).status_code == 422
    assert (await client.delete("/api/v1/documents/0")).status_code == 422
