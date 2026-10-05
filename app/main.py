from contextlib import asynccontextmanager
from pathlib import Path as FsPath
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, get_settings
from app.db import create_tables, make_engine, make_sessionmaker
from app.errors import http_error_message, validation_error_message
from app.schemas import DocumentOut, ErrorOut, HealthOut
from app.search import SearchIndex
from app.service import DocumentService

STATIC_DIR = FsPath(__file__).parent / "static"


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
        title="Поиск по документам",
        version="1.0.0",
        description="Простой поисковик по текстам документов (PostgreSQL + Elasticsearch).",
        openapi_tags=[
            {"name": "Документы", "description": "Поиск и удаление документов"},
            {"name": "Сервис", "description": "Служебные методы"},
        ],
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": validation_error_message(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def on_http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": http_error_message(exc)},
            headers=getattr(exc, "headers", None),
        )

    def get_service(request: Request) -> DocumentService:
        return request.app.state.service

    Service = Annotated[DocumentService, Depends(get_service)]

    @app.get(
        "/api/v1/documents/search",
        response_model=list[DocumentOut],
        tags=["Документы"],
        summary="Поиск документов",
        description=(
            "Ищет по тексту документа в индексе и возвращает до 20 самых релевантных "
            "документов со всеми полями БД, упорядоченных по дате создания (новые сверху)."
        ),
        responses={
            200: {"description": "Найденные документы"},
            422: {"model": ErrorOut, "description": "Некорректный запрос"},
        },
    )
    async def search_documents(
        service: Service,
        query: Annotated[
            str, Query(min_length=1, max_length=1000, description="Текст запроса", examples=["кот"])
        ],
    ):
        query = query.strip()
        if not query:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Запрос не может быть пустым")
        return await service.search(query)

    @app.delete(
        "/api/v1/documents/{doc_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Документы"],
        summary="Удаление документа",
        description="Удаляет документ из БД и поискового индекса по id.",
        responses={
            204: {"description": "Документ удалён"},
            404: {"model": ErrorOut, "description": "Документ не найден"},
            422: {"model": ErrorOut, "description": "Некорректный запрос"},
        },
    )
    async def delete_document(
        service: Service, doc_id: Annotated[int, Path(ge=1, description="Идентификатор документа")]
    ):
        if not await service.delete(doc_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Документ не найден")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/health",
        response_model=HealthOut,
        tags=["Сервис"],
        summary="Проверка работоспособности",
        responses={200: {"description": "Сервис работает"}},
    )
    async def health():
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def index_page():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/docs", include_in_schema=False)
    async def swagger_page():
        html = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title="Поиск по документам — документация API",
            swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "list"},
        ).body.decode()
        translate = (STATIC_DIR / "swagger-ru.js").read_text(encoding="utf-8")
        html = html.replace("</body>", f"<script>{translate}</script></body>")
        html = html.replace("<html>", '<html lang="ru">', 1)
        return HTMLResponse(html)

    return app


app = create_app()
