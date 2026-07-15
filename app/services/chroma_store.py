import chromadb
from chromadb.utils import embedding_functions

from app.config import settings


class ChromaStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_dir)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=self.embedding_fn,
        )

    def upsert_resume(self, doc_id: str, text: str, metadata: dict) -> None:
        self.collection.upsert(ids=[doc_id], documents=[text], metadatas=[metadata])

    def query(self, query_text: str, n_results: int = 5, where: dict | None = None) -> dict:
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

    def get_by_id(self, doc_id: str) -> dict:
        return self.collection.get(ids=[doc_id])

    def list_all(self) -> dict:
        return self.collection.get()


_store: ChromaStore | None = None


def get_store() -> ChromaStore:
    global _store
    if _store is None:
        _store = ChromaStore()
    return _store
