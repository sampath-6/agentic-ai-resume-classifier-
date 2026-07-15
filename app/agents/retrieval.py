from app.config import settings
from app.services.chroma_store import get_store
from app.state import GraphState


def retrieval_agent(state: GraphState) -> dict:
    store = get_store()
    attempts = state.get("broaden_attempts", 0)

    # first attempt honors any metadata filter (e.g. seniority); if that yields
    # nothing, the loop broadens by dropping the filter and relying on semantic search alone
    where = state.get("where_filter") if attempts == 0 else None

    results = store.query(state["query_text"], n_results=settings.top_k, where=where)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    retrieved = [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(docs, metas, dists)
    ]

    return {"retrieved": retrieved, "broaden_attempts": attempts + 1}
