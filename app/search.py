from collections.abc import Iterable

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

INDEX_SETTINGS = {
    "analysis": {
        "analyzer": {
            "text_ru_en": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "russian_stop", "russian_stemmer", "english_stemmer"],
            }
        },
        "filter": {
            "russian_stop": {"type": "stop", "stopwords": "_russian_"},
            "russian_stemmer": {"type": "stemmer", "language": "russian"},
            "english_stemmer": {"type": "stemmer", "language": "english"},
        },
    }
}

INDEX_MAPPINGS = {
    "properties": {
        "id": {"type": "long"},
        "text": {"type": "text", "analyzer": "text_ru_en"},
    }
}


class SearchIndex:
    def __init__(self, client: AsyncElasticsearch, index: str) -> None:
        self.client = client
        self.index = index

    async def ensure_index(self, recreate: bool = False) -> None:
        exists = await self.client.indices.exists(index=self.index)
        if exists and recreate:
            await self.client.indices.delete(index=self.index)
            exists = False
        if not exists:
            await self.client.indices.create(
                index=self.index, settings=INDEX_SETTINGS, mappings=INDEX_MAPPINGS
            )

    async def index_documents(self, docs: Iterable[tuple[int, str]], refresh: bool = False) -> None:
        actions = (
            {"_index": self.index, "_id": str(doc_id), "_source": {"id": doc_id, "text": text}}
            for doc_id, text in docs
        )
        await async_bulk(self.client, actions, refresh=refresh)

    async def search_ids(self, query: str, limit: int) -> list[int]:
        resp = await self.client.search(
            index=self.index,
            query={"match": {"text": {"query": query}}},
            size=limit,
            source=False,
        )
        return [int(hit["_id"]) for hit in resp["hits"]["hits"]]

    async def delete(self, doc_id: int, refresh: bool = False) -> bool:
        try:
            await self.client.delete(index=self.index, id=str(doc_id), refresh=refresh)
        except NotFoundError:
            return False
        return True

    async def refresh(self) -> None:
        await self.client.indices.refresh(index=self.index)
