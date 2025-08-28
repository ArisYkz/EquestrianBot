import os, traceback, multiprocessing
from typing import Optional, List

import pandas as pd
import torch
import numpy as np

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from ingestion import upsert_documents
import faiss

# ------------------------ Config ------------------------

MODEL_DIR = os.environ.get("PHI3_MODEL_DIR", r"D:\Models\phi3-equestrian-merged-fp16")
PRODUCTS_CSV_PATH = r"C:\Users\R9000P\Desktop\IA\ml\data\products.csv"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

try:
    n_threads = max(2, min(8, (os.cpu_count() or multiprocessing.cpu_count() or 4)))
    torch.set_num_threads(n_threads)
    torch.set_num_interop_threads(max(1, n_threads // 2))
except Exception:
    pass

# ------------------------ Load Models ------------------------

print("Loading main model from:", MODEL_DIR)
tok = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    trust_remote_code=True,
    device_map="auto",
    low_cpu_mem_usage=True,
).eval()
print(f"✅ Model READY on {DEVICE}")

print("Loading embedding model...")
embed_model = SentenceTransformer(EMBED_MODEL_NAME, device=DEVICE)
print("✅ Embedding model loaded.")

# ------------------------ Load Shipping Policy ------------------------

def load_policy_text() -> str:
    for path in ("shipping_policy.md", "policies/shipping.md", "policy/shipping.md"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    return os.environ.get("SHIP_POLICY", "").strip()

POLICY_TEXT = load_policy_text()

# ------------------------ Product Index ------------------------

product_df = None
product_index = None
product_embeddings = None

def build_product_index(csv_path=PRODUCTS_CSV_PATH, limit=100):
    global product_df, product_index, product_embeddings
    try:
        product_df = pd.read_csv(csv_path).head(limit)
        texts = []

        for _, row in product_df.iterrows():
            name = str(row.get("Name", ""))
            desc = str(row.get("Description", ""))
            cat = str(row.get("Category", ""))
            price = str(row.get("Price", ""))
            stock = str(row.get("StockQuantity", ""))
            summary = f"{name}. {desc}. Category: {cat}. Price: ${price}. Stock: {stock}."
            texts.append(summary)

        product_embeddings = embed_model.encode(texts, normalize_embeddings=True)
        dim = product_embeddings.shape[1]

        product_index = faiss.IndexFlatIP(dim)
        product_index.add(product_embeddings)
        print(f"✅ Indexed {len(texts)} products.")
    except Exception as e:
        print("❌ Failed to build product index:", e)

build_product_index()

def retrieve_top_products(query: str, top_k=4) -> str:
    if product_index is None or product_df is None:
        return ""
    try:
        q_emb = embed_model.encode([query], normalize_embeddings=True)
        scores, indices = product_index.search(q_emb, top_k)

        lines = []
        for idx in indices[0]:
            row = product_df.iloc[idx]
            lines.append(f"- {row['Name']} ({row['Category']}): {row['Description']} Price: ${row['Price']}, Stock: {row['StockQuantity']}")
        return "\n".join(lines)
    except Exception as e:
        print("❌ Retrieval error:", e)
        return ""

# ------------------------ Prompt Construction ------------------------

BASE_SYSTEM = (
    "You are a helpful assistant for an equestrian apparel store. "
    "Give complete product suggestions in full sentences, with names, prices, stock, and categories. "
    "Be concise, friendly, and informative. Compare items when helpful."
)

def build_prompt(user_input: str, product_info: str = "") -> str:
    prompt = f"<|system|>\n{BASE_SYSTEM}"
    if POLICY_TEXT:
        prompt += f"\n\n[Store Shipping Policy]\n{POLICY_TEXT}"
    if product_info:
        prompt += f"\n\n[Relevant Product Matches]\n{product_info}"
    prompt += f"\n<|end|>\n<|user|>\n{user_input.strip()}\n<|end|>\n<|assistant|>\n"
    return prompt

# ------------------------ FastAPI App ------------------------

app = FastAPI(title="Phi-3 Equestrian Sidecar")
_last_error: Optional[str] = None

class GenRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200
    min_new_tokens: int = 120
    temperature: float = 0.4
    top_p: float = 0.92
    max_time: float = 45.0

class GenResponse(BaseModel):
    text: str

@app.get("/", response_class=PlainTextResponse)
def root():
    return "Phi-3 EquestrianBot is running.\nDocs at http://127.0.0.1:8000/docs"

@app.get("/health")
def health():
    return {"status": "ready", "device": DEVICE}

@app.post("/reload_products")
def reload_products():
    build_product_index()
    return {"status": "ok"}

@app.get("/last_error")
def last_error():
    return {"status": "ok" if not _last_error else "error", "error": _last_error}

@app.post("/generate", response_model=GenResponse)
def generate(req: GenRequest):
    global _last_error
    _last_error = None
    try:
        context = retrieve_top_products(req.prompt)
        full_prompt = build_prompt(req.prompt, context)

        tokenized_input = tok(
            full_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1536,
            padding=False
        )
        tokenized_input = {k: v.to(DEVICE) for k, v in tokenized_input.items()}

        with torch.inference_mode():
            out = model.generate(
                **tokenized_input,
                max_new_tokens=req.max_new_tokens,
                min_new_tokens=req.min_new_tokens,
                do_sample=True,
                temperature=req.temperature,
                top_p=req.top_p,
                bad_words_ids=None,
                repetition_penalty=1.05,
                no_repeat_ngram_size=3,
                max_time=req.max_time,
                pad_token_id=tok.eos_token_id,
                eos_token_id=tok.eos_token_id,
            )

        new_tokens = out[0, tokenized_input["input_ids"].shape[1]:]
        text = tok.decode(new_tokens, skip_special_tokens=True).strip().split("<|end|>")[0]
        return GenResponse(text=text)

    except Exception as e:
        _last_error = "".join(traceback.format_exception(e))
        return JSONResponse(status_code=500, content={"error": "generation_failed", "detail": _last_error})
