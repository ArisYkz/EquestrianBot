import os, json
from typing import List, Dict
import numpy as np

# pip install sentence-transformers faiss-cpu
from sentence_transformers import SentenceTransformer
import faiss

VEC_DIR = os.path.join(os.path.dirname(__file__), "vectorstores")
EMB_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_model = SentenceTransformer(EMB_MODEL)

def _tenant_dir(tenant_id: str):
    d = os.path.join(VEC_DIR, tenant_id)
    os.makedirs(d, exist_ok=True)
    return d

def _index_paths(tenant_id: str):
    base = _tenant_dir(tenant_id)
    return (
        os.path.join(base, "index.faiss"),
        os.path.join(base, "id_map.json"),   # id -> row and metadata store
        os.path.join(base, "docs.json")      # raw docs by id
    )

def _load_index(index_path: str, dim: int):
    if os.path.exists(index_path):
        return faiss.read_index(index_path)
    # Use Inner Product with normalized vectors for cosine similarity
    index = faiss.IndexFlatIP(dim)
    return index

def _normalize(v: np.ndarray):
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms

def _make_text_for_embedding(doc: Dict):
    # Build a consistent text representation
    if doc.get("question") or doc.get("answer"):
        return f"Q: {doc.get('question','')}\nA: {doc.get('answer','')}\n" \
               f"Title: {doc.get('title','')}\nURL: {doc.get('url','')}\n" \
               f"Tags: {', '.join(doc.get('tags',[]) or [])}"
    # products
    attrs = doc.get("attributes") or {}
    attrs_text = " ".join([f"{k}: {v}" for k, v in attrs.items()])
    return f"Title: {doc.get('title','')}\n{attrs_text}\nURL: {doc.get('url','')}"

def upsert_documents(tenant_id: str, dataset_type: str, documents: List[Dict]) -> int:
    # Load existing artifacts
    index_path, idmap_path, docs_path = _index_paths(tenant_id)

    # Encode all docs
    texts = [_make_text_for_embedding(d) for d in documents]
    emb = _model.encode(texts, convert_to_numpy=True)
    emb = _normalize(emb.astype("float32"))
    dim = emb.shape[1]

    # Load or create index
    index = _load_index(index_path, dim)

    # Load id_map and docs
    id_map = {}
    if os.path.exists(idmap_path):
        with open(idmap_path, "r", encoding="utf-8") as f:
            id_map = json.load(f)

    docs_store = {}
    if os.path.exists(docs_path):
        with open(docs_path, "r", encoding="utf-8") as f:
            docs_store = json.load(f)

    # Build arrays for new vectors and ids, but handle upsert
    # We emulate upsert by: if id exists, mark to replace (faiss flat index has no delete; simple approach: rebuild)
    existing_ids = list(id_map.keys())
    new_ids = [d["id"] for d in documents]

    need_rebuild = any(i in existing_ids for i in new_ids) and index.ntotal > 0

    if need_rebuild:
        # Rebuild: merge old docs with replacements
        for d in documents:
            docs_store[d["id"]] = d
        # Re-encode ALL docs
        all_docs = list(docs_store.values())
        all_texts = [_make_text_for_embedding(d) for d in all_docs]
        all_emb = _normalize(_model.encode(all_texts, convert_to_numpy=True).astype("float32"))

        # Recreate index
        index = faiss.IndexFlatIP(all_emb.shape[1])
        index.add(all_emb)

        # New id_map: row -> id
        id_map = {doc["id"]: idx for idx, doc in enumerate(all_docs)}

    else:
        # Pure append (fast path)
        start_id = index.ntotal
        index.add(emb)
        for i, d in enumerate(documents):
            docs_store[d["id"]] = d
            id_map[d["id"]] = start_id + i

    # Persist
    faiss.write_index(index, index_path)
    with open(idmap_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False, indent=2)
    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(docs_store, f, ensure_ascii=False, indent=2)

    return len(documents)
