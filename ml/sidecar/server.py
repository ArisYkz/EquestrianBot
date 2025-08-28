import os, sys, time, traceback
from typing import List, Dict, Optional
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

# ensure local imports work when running via uvicorn
sys.path.insert(0, os.path.dirname(__file__))

from ingestion import upsert_documents
from retrieval import search
from generation import generate_from_context
from cache import get as cache_get, put as cache_put

# ------------- FastAPI -------------
app = FastAPI(title="RAG Sidecar (Phi-3)")

# --------- Schemas ----------
class Document(BaseModel):
    id: str
    title: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, object]] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, object]] = None

class IngestRequest(BaseModel):
    tenant_id: str
    dataset_type: str
    documents: List[Document]

class QueryRequest(BaseModel):
    tenant_id: str
    query: str
    top_k: int = 4

class QueryResponse(BaseModel):
    answer: str
    strategy: str
    latency_ms: int
    context: List[Dict[str, object]]


# --------- Routes ----------
@app.get("/", response_class=PlainTextResponse)
def root():
    return "RAG Sidecar is running.\nDocs at http://127.0.0.1:8000/docs"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(req: IngestRequest):
    try:
        count = upsert_documents(
            req.tenant_id,
            req.dataset_type,
            [d.model_dump() for d in req.documents]
        )
        return {"status": "ingested", "count": count}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": "ingest_failed",
            "detail": "".join(traceback.format_exception(e))
        })


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    t0 = time.time()

    try:
        # 1. cache check
        cached = cache_get(req.tenant_id, req.query)
        if cached:
            latency = int((time.time() - t0) * 1000)
            return QueryResponse(
                answer=cached,
                strategy="cache",
                latency_ms=latency,
                context=[]
            )

        # 2. retrieve docs
        ctx = search(req.tenant_id, req.query, top_k=req.top_k)

        # 3. generate answer
        answer, meta = generate_from_context(req.query, ctx)

        # 4. update cache
        cache_put(req.tenant_id, req.query, answer)

        latency = int((time.time() - t0) * 1000)
        return QueryResponse(
            answer=answer,
            strategy="rag",
            latency_ms=latency,
            context=ctx
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": "query_failed",
            "detail": "".join(traceback.format_exception(e))
        })

@app.get("/list/{tenant_id}")
def list_docs(tenant_id: str):
    try:
        index, inv_map, docs_store = _load_artifacts(tenant_id)
        return list(docs_store.values())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/delete/{tenant_id}")
def delete_tenant(tenant_id: str):
    try:
        # remove vectorstore folder for this tenant
        path = f"vectorstores/{tenant_id}"
        import shutil, os
        if os.path.exists(path):
            shutil.rmtree(path)
        return {"status": "deleted", "tenant": tenant_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/delete/{tenant_id}/{doc_id}")
def delete_doc(tenant_id: str, doc_id: str):
    try:
        index, inv_map, docs_store = _load_artifacts(tenant_id)
        if doc_id in docs_store:
            del docs_store[doc_id]
            # save updated docs_store (persistence logic as needed)
            import json, os
            with open(f"vectorstores/{tenant_id}/docs.json", "w", encoding="utf-8") as f:
                json.dump(list(docs_store.values()), f, ensure_ascii=False, indent=2)
        return {"status": "deleted", "tenant": tenant_id, "doc": doc_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

