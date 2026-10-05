from contextlib import asynccontextmanager
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response, status

from app.config import Settings, get_settings
from app.db import create_tables, make_engine, make_sessionmaker
from app.schemas import DocumentOut, ErrorOut
from app.search import SearchIndex
from app.service import DocumentService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        es = AsyncElasticsearch(settings.es_url)
        index = SearchIndex(es, settings.es_index)
        await create_tables(engine)
        await index.ensure_index()
        app.state.engine = engine
        app.state.index = index
        app.state.service = DocumentService(make_sessionmaker(engine), index, settings.search_limit)
        try:
            yield
        finally:
            await es.close()
            await engine.dispose()

    app = FastAPI(
        title="Document Search Service",
        version="1.0.0",
        description="Простой поисковик по текстам документов (PostgreSQL + Elasticsearch).",
        lifespan=lifespan,
    )

    def get_service(request: Request) -> DocumentService:
        return request.app.state.service

    Service = Annotated[DocumentService, Depends(get_service)]

    @app.get(
        "/api/v1/documents/search",
        response_model=list[DocumentOut],
        tags=["documents"],
        summary="Поиск документов",
        description=(
            "Ищет по тексту документа в индексе и возвращает до 20 самых релевантных "
            "документов со всеми полями БД, упорядоченных по дате создания (новые сверху)."
        ),
    )
    async def search_documents(
        service: Service,
        query: Annotated[str, Query(min_length=1, max_length=1000, description="Текст запроса")],
    ):
        query = query.strip()
        if not query:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Query must not be blank")
        return await service.search(query)

    @app.delete(
        "/api/v1/documents/{doc_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["documents"],
        summary="Удаление документа",
        description="Удаляет документ из БД и поискового индекса по id.",
        responses={404: {"model": ErrorOut, "description": "Документ не найден"}},
    )
    async def delete_document(service: Service, doc_id: Annotated[int, Path(ge=1)]):
        if not await service.delete(doc_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/health", tags=["service"], summary="Проверка работоспособности")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
