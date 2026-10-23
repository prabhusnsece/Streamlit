"""Model helpers shared by the notebook, rag_core.py and app.py.

LLM        : Groq API (OpenAI-compatible endpoint). Set GROQ_API_KEY. Override the model with LLM_MODEL.
Judge      : a second Groq model (env JUDGE_MODEL) so the evaluator is not the generator.
Embeddings : sentence-transformers models running locally on CPU / CUDA / Apple MPS.
"""
import os, json, urllib.request
import torch
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")              # fast and cheap; the old llama-3.x ids were retired on Groq
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b")         # different model from the generator => less lenient judge
RERANKER_MODEL = "BAAI/bge-reranker-base"

if torch.cuda.is_available():
    DEVICE = "cuda"
elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# name -> (huggingface id, query prefix, document prefix)
EMBEDDER_SPECS = {
    "bge-base":     ("BAAI/bge-base-en-v1.5",              BGE_QUERY_PREFIX, ""),   # fast, 768-d
    "mxbai-large":  ("mixedbread-ai/mxbai-embed-large-v1", BGE_QUERY_PREFIX, ""),   # 1024-d
    "bge-m3":       ("BAAI/bge-m3",                        "",               ""),   # 1024-d, multilingual, slower
}


class LocalEmbedder(Embeddings):
    """LangChain-compatible wrapper with explicit query/document prefixes and normalised vectors (cosine-ready)."""

    def __init__(self, model_id, query_prefix="", doc_prefix="", batch_size=16, max_seq_length=512):
        self.model_id = model_id
        self.model = SentenceTransformer(model_id, device=DEVICE)
        self.model.max_seq_length = min(self.model.max_seq_length, max_seq_length)
        if DEVICE == "cuda":
            self.model.half()
        self.qp, self.dp, self.bs = query_prefix, doc_prefix, batch_size

    def embed_documents(self, texts):
        vecs = self.model.encode([self.dp + t for t in texts], batch_size=self.bs,
                                 normalize_embeddings=True, show_progress_bar=len(texts) > 64)
        return vecs.tolist()

    def embed_query(self, text):
        return self.model.encode(self.qp + text, normalize_embeddings=True).tolist()


def get_embedder(name):
    model_id, qp, dp = EMBEDDER_SPECS[name]
    return LocalEmbedder(model_id, qp, dp)


# ---------------------------------------------------------------- Groq helpers
def get_groq_key(prompt=False):
    """Look for the key in: env var -> Streamlit secrets (deployed app) -> Colab secrets -> (optional) hidden prompt."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        try:
            import streamlit as st
            key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
        except Exception:
            key = ""
    if not key:
        try:
            from google.colab import userdata
            key = (userdata.get("GROQ_API_KEY") or "").strip()
        except Exception:
            key = ""
    if not key and prompt:
        try:
            from getpass import getpass
            key = getpass("Groq API key (console.groq.com/keys): ").strip()
        except Exception:
            key = ""
    if key:
        os.environ["GROQ_API_KEY"] = key        # so every later call (and rag_core / app.py) finds it
    return key


def get_llm(json_mode=False, model=None, max_tokens=None, effort="low"):
    from langchain_openai import ChatOpenAI
    key = get_groq_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Create a key at https://console.groq.com/keys and set it as an "
                           "environment variable, a Colab secret, or a Streamlit secret.")
    name = model or LLM_MODEL
    extra = {}
    if name.startswith("openai/gpt-oss"):
        extra["reasoning_effort"] = effort    # gpt-oss models think before answering; "low" keeps RAG answers fast
    if json_mode:
        extra["response_format"] = {"type": "json_object"}
    kwargs = dict(model=name, api_key=key, base_url=GROQ_BASE_URL, temperature=0, seed=42, timeout=90, max_retries=5)
    if max_tokens:
        kwargs["max_tokens"] = max_tokens     # reasoning models spend part of this budget on thinking, so keep it generous
    if extra:
        kwargs["model_kwargs"] = extra
    return ChatOpenAI(**kwargs)


def check_groq(models=None):
    """Fail early with an actionable message if the key is missing/invalid or a model is not available to this key."""
    key = get_groq_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Get a key at https://console.groq.com/keys.")
    req = urllib.request.Request(f"{GROQ_BASE_URL}/models", headers={"Authorization": f"Bearer {key}", "User-Agent": "rag-research-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            names = [m["id"] for m in json.load(r).get("data", [])]
    except Exception as e:
        raise RuntimeError(f"Could not reach the Groq API at {GROQ_BASE_URL} (bad key, no internet or no credits?). Details: {e}")
    for m in (models or [LLM_MODEL]):
        if m not in names:
            raise RuntimeError(f"Model '{m}' is not available to this API key. Available: {names}\n"
                               f"Set LLM_MODEL / JUDGE_MODEL to one of them.")
    return names
