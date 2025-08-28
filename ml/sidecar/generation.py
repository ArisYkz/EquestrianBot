import os, torch
from typing import List, Dict, Any, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM

# -------- Config --------
MODEL_DIR = os.environ.get("PHI3_MODEL_DIR", r"D:\Models\phi3-equestrian-merged-fp16")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# -------- Load Phi-3 once --------
_tok = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True)
_tok.pad_token = _tok.eos_token
_model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float16,   # use FP16 for GPU efficiency
    trust_remote_code=True,
    device_map=None              # force full load on single device
).to("cuda").eval()



# -------- System instruction --------
SYSTEM_MSG = (
    "You are a helpful SaaS support assistant.\n"
    "You must ONLY answer using the provided context snippets.\n"
    "If the answer is not in the context, reply exactly: \"I don't know.\".\n"
    "Always finish with a 'Sources:' list showing titles or URLs."
)


def _format_context(ctx: List[Dict[str, Any]]) -> str:
    """Convert retrieved docs into a readable context block for the prompt."""
    lines = []
    for i, c in enumerate(ctx, 1):
        title = c.get("title") or c.get("url") or c.get("id") or f"Doc{i}"
        if c.get("question") or c.get("answer"):
            snippet = f"Q: {c.get('question','')}\nA: {c.get('answer','')}"
        else:
            attrs = c.get("attributes") or {}
            if attrs:
                kv = "; ".join([f"{k}: {v}" for k, v in attrs.items()])
                snippet = kv
            else:
                snippet = str(c.get("raw") or "")
        lines.append(f"[{title}] (score={c.get('score'):.3f})\n{snippet}")
    return "\n\n".join(lines)


def build_prompt(user_query: str, ctx: List[Dict[str, Any]]) -> str:
    """Build strict grounded prompt."""
    ctx_block = _format_context(ctx) if ctx else "No relevant context retrieved."
    return (
        f"<|system|>\n{SYSTEM_MSG}\n<|end|>\n"
        f"<|user|>\nQuestion: {user_query}\n\nContext:\n{ctx_block}\n<|end|>\n"
        f"<|assistant|>\n"
    )


def generate_from_context(
    user_query: str,
    ctx: List[Dict[str, Any]],
    *,
    temperature: float = 0.4,
    top_p: float = 0.92,
    max_new_tokens: int = 220,
    min_new_tokens: int = 64,
    max_time: float = 45.0,
) -> Tuple[str, Dict[str, Any]]:
    """Generate an answer from Phi-3 given retrieved docs."""
    prompt = build_prompt(user_query, ctx)
    tokens = _tok(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1536,
        padding=False
    )
    tokens = {k: v.to(DEVICE) for k, v in tokens.items()}

    with torch.inference_mode():
        out = _model.generate(
            **tokens,
            max_new_tokens=max_new_tokens,
            min_new_tokens=min_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=1.05,
            no_repeat_ngram_size=3,
            max_time=max_time,
            pad_token_id=_tok.eos_token_id,
            eos_token_id=_tok.eos_token_id,
        )

    new_tokens = out[0, tokens["input_ids"].shape[1]:]
    text = _tok.decode(new_tokens, skip_special_tokens=True).strip().split("<|end|>")[0]

    return text, {
        "prompt_len": int(tokens["input_ids"].shape[1]),
        "gen_len": int(new_tokens.shape[0]),
    }
