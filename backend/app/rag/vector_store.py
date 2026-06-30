"""
RAG layer: Chroma vector DB + sentence-transformers embeddings.
Supports hybrid retrieval: vector similarity + simple keyword boost.
"""
import os
import uuid
import re
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

os.makedirs(CHROMA_DIR, exist_ok=True)

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

_collection = _client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=_embed_fn,
    metadata={"hnsw:space": "cosine"},
)


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def add_documents(texts: list[str], source: str = "user_upload", extra_meta: dict | None = None):
    """Chunk and store documents in the vector DB."""
    ids, docs, metas = [], [], []
    for t in texts:
        for chunk in _chunk_text(t):
            ids.append(str(uuid.uuid4()))
            docs.append(chunk)
            meta = {"source": source}
            if extra_meta:
                meta.update(extra_meta)
            metas.append(meta)
    if docs:
        _collection.add(ids=ids, documents=docs, metadatas=metas)
    return len(docs)


def query(query_text: str, top_k: int = 5):
    """Hybrid-ish retrieval: vector search + simple keyword overlap re-rank."""
    count = _collection.count()
    if count == 0:
        return []
    results = _collection.query(query_texts=[query_text], n_results=min(top_k * 2, max(count, 1)))
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    keywords = set(re.findall(r"\w+", query_text.lower()))

    scored = []
    for doc, meta, dist in zip(docs, metas, dists):
        kw_overlap = len(keywords & set(re.findall(r"\w+", doc.lower())))
        vector_score = 1 - dist  # cosine distance -> similarity
        hybrid_score = 0.75 * vector_score + 0.25 * (kw_overlap / max(len(keywords), 1))
        scored.append({"text": doc, "metadata": meta, "score": round(hybrid_score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def stats():
    return {"total_chunks": _collection.count()}
