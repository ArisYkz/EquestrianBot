import os, json
from typing import List, Dict, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# -------- Config --------
VEC_DIR = os.path.join(os.path.dirname(__file__), "vectorstores")
EMB_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_embedder = SentenceTransformer(EMB_MODEL)


def _normalize(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms


def _paths(tenant_id: str):
    base = os.path.join(VEC_DIR, tenant_id)
    return (
        os.path.join(base, "index.faiss"),
        os.path.join(base, "id_map.json"),
        os.path.join(base, "docs.json"),
    )


def _load_artifacts(tenant_id: str):
    index_path, idmap_path, docs_path = _paths(tenant_id)

    if not (os.path.exists(index_path) and os.path.exists(idmap_path) and os.path.exists(docs_path)):
        raise FileNotFoundError(f"No vector store found for tenant '{tenant_id}'. Please ingest first.")

    index = faiss.read_index(index_path)
    with open(idmap_path, "r", encoding="utf-8") as f:
        id_map: Dict[str, int] = json.load(f)
    with open(docs_path, "r", encoding="utf-8") as f:
        docs_store: Dict[str, Dict[str, Any]] = json.load(f)

    # Invert mapping row -> doc_id
    inv_map = {row: doc_id for doc_id, row in id_map.items()}
    return index, inv_map, docs_store


def search(tenant_id: str, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Return top_k retrieved documents for a tenant query."""
    index, inv_map, docs_store = _load_artifacts(tenant_id)

    qv = _embedder.encode([query], convert_to_numpy=True).astype("float32")
    qv = _normalize(qv)
    scores, rows = index.search(qv, top_k)

    results: List[Dict[str, Any]] = []
    for score, row in zip(scores[0], rows[0]):
        if row == -1:
            continue
        doc_id = inv_map.get(int(row))
        if not doc_id:
            continue
        d = docs_store.get(doc_id, {})
        results.append({
            "id": doc_id,
            "title": d.get("title"),
            "url": d.get("url"),
            "score": float(score),
            "attributes": d.get("attributes", {}),
            "question": d.get("question"),
            "answer": d.get("answer"),
            "metadata": d.get("metadata", {}),
            "tags": d.get("tags", []),
            "raw": d  # keep full doc for prompt
        })

    return results
