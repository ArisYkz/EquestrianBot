import time
from typing import Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

# -------- Config --------
_EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_embedder = SentenceTransformer(_EMB_MODEL)

# Cache: {(tenant_id, query): (answer, embedding, timestamp)}
_cache: Dict[Tuple[str, str], Tuple[str, np.ndarray, float]] = {}

# TTL and similarity threshold
TTL_SECONDS = 1800        # expire after 30 minutes
SIM_THRESHOLD = 0.92      # cosine similarity threshold for hit


def _embed(text: str) -> np.ndarray:
    """Embed and normalize a single text string."""
    v = _embedder.encode([text], convert_to_numpy=True).astype("float32")
    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return v[0]


def get(tenant_id: str, query: str) -> Optional[str]:
    """Check cache for a semantically close query. Return answer if hit."""
    now = time.time()
    qv = _embed(query)

    best_sim, best_ans = -1.0, None
    for (tid, q), (ans, emb, ts) in list(_cache.items()):
        if tid != tenant_id:
            continue
        # expire old entries
        if now - ts > TTL_SECONDS:
            del _cache[(tid, q)]
            continue
        sim = float(np.dot(qv, emb))
        if sim > best_sim:
            best_sim, best_ans = sim, ans

    if best_sim >= SIM_THRESHOLD:
        return best_ans
    return None


def put(tenant_id: str, query: str, answer: str) -> None:
    """Store query + answer in cache."""
    try:
        _cache[(tenant_id, query)] = (answer, _embed(query), time.time())
    except Exception:
        pass  # fail silently
