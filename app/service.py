from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import Document
from app.search import SearchIndex


class DocumentService:
    def __init__(self, sessionmaker: async_sessionmaker, index: SearchIndex, limit: int = 20) -> None:
        self.sessionmaker = sessionmaker
        self.index = index
        self.limit = limit

    async def search(self, query: str) -> list[Document]:
        ids = await self.index.search_ids(query, self.limit)
        if not ids:
            return []
        async with self.sessionmaker() as session:
            result = await session.scalars(
                select(Document)
                .where(Document.id.in_(ids))
                .order_by(Document.created_date.desc(), Document.id.desc())
            )
            return list(result)

    async def delete(self, doc_id: int) -> bool:
        # delete from ES inside the DB transaction so a failure rolls back the row
        async with self.sessionmaker() as session, session.begin():
            deleted = await session.scalar(
                delete(Document).where(Document.id == doc_id).returning(Document.id)
            )
            in_index = await self.index.delete(doc_id, refresh=True)
            return deleted is not None or in_index
