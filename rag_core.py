"""Shared RAG engine for app.py. Loads the artifacts the notebook saved (index, chunks, selected settings)."""
import os, re, joblib
from pathlib import Path
from collections import defaultdict

import numpy as np
import chromadb
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from local_models import DEVICE, RERANKER_MODEL, LLM_MODEL, get_embedder, get_llm

ARTIFACTS = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
POOL, MAX_MSGS = 20, 6
STRATEGIES = ["dense", "mmr", "bm25", "hybrid_rrf", "hybrid_rerank", "multiquery_rerank"]

SYSTEM = (
    "You are a research assistant answering questions about AI research papers.\n"
    "Rules:\n"
    "1. Answer ONLY using the numbered context passages below. Do not use outside knowledge.\n"
    "2. If the context does not contain enough information, reply exactly: "
    "\"I don't know based on the provided papers.\"\n"
    "3. Cite supporting passages inline as [1], [2], [3].\n"
    "4. Be concise and precise; keep technical terms and numbers exactly as in the context.\n\n"
    "Context:\n{context}"
)
CONDENSE_SYSTEM = (
    "You rewrite a follow-up message into ONE standalone search question.\n"
    "Use the chat history only to resolve pronouns and references. Output ONLY the rewritten question on a single line. "
    "NEVER answer the question. If the message is already standalone, repeat it unchanged.\n\n"
    "Example\nHistory:\nUser: What is LoRA?\nAssistant: LoRA adds low-rank adapter matrices to frozen weights.\n"
    "Follow-up: How does it reduce memory?\nStandalone question: How does LoRA reduce memory usage?"
)


def _tok(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def rrf(rank_lists, k=60):
    scores, by_id = defaultdict(float), {}
    for lst in rank_lists:
        for r, d in enumerate(lst):
            cid = d.metadata["chunk_id"]
            scores[cid] += 1.0 / (k + r + 1)
            by_id[cid] = d
    return [by_id[c] for c, _ in sorted(scores.items(), key=lambda x: -x[1])]


def format_docs(docs):
    return "\n\n".join(f"[{i}] {d.metadata['paper_title']} (p. {d.metadata['page']})\n{d.page_content}"
                       for i, d in enumerate(docs, 1))


def sources_of(docs):
    return [{"rank": i, "paper_title": d.metadata["paper_title"], "page": d.metadata["page"],
             "source": d.metadata["source"], "snippet": d.page_content[:300] + "..."} for i, d in enumerate(docs, 1)]


class RAGEngine:
    def __init__(self):
        meta_path = ARTIFACTS / "index_meta.pkl"
        if not meta_path.exists():
            raise FileNotFoundError(f"{meta_path} not found. Run the notebook (Sections 1-5) first.")
        self.meta = joblib.load(meta_path)
        self.chunks = self.meta["chunks"]
        client = chromadb.PersistentClient(path=str(ARTIFACTS / "chroma"))
        self.store = Chroma(collection_name=self.meta["collection"], client=client,
                            embedding_function=get_embedder(self.meta["embedding"]))
        self.bm25 = BM25Okapi([_tok(d.page_content) for d in self.chunks])
        self._reranker = None                       # loaded lazily: saves ~1 GB RAM when no rerank strategy is used
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM), MessagesPlaceholder("chat_history", optional=True), ("human", "{question}")])
        self.answer_chain = self.prompt | self.llm | StrOutputParser()
        self.condense_chain = ChatPromptTemplate.from_messages(
            [("system", CONDENSE_SYSTEM), ("human", "History:\n{history}\nFollow-up: {question}\nStandalone question:")]
        ) | self.llm | StrOutputParser()
        self.mq_chain = ChatPromptTemplate.from_template(
            "Write 3 different search queries (one per line, no numbering, no extra text) that would retrieve passages "
            "from research papers to answer:\n{question}") | self.llm | StrOutputParser()
        self.sessions = {}

    # ---- info for the UI
    def info(self):
        return {"chunks": len(self.chunks), "papers": len({d.metadata["paper_id"] for d in self.chunks}),
                "chunking": self.meta["chunking"], "embedding": self.meta["embedding"], "llm": LLM_MODEL}

    # ---- retrievers
    def _bm25(self, q, k):
        s = self.bm25.get_scores(_tok(q))
        return [self.chunks[i] for i in np.argsort(s)[::-1][:k]]

    def _hybrid(self, q, k=3, pool=POOL):
        return rrf([self.store.similarity_search(q, k=pool), self._bm25(q, pool)])[:k]

    @property
    def reranker(self):
        if self._reranker is None:
            self._reranker = CrossEncoder(RERANKER_MODEL, device=DEVICE)
        return self._reranker

    def _rerank(self, q, docs, k=3):
        sc = self.reranker.predict([(q, d.page_content) for d in docs])
        return [docs[i] for i in np.argsort(sc)[::-1][:k]]

    def retrieve(self, q, strategy=None, k=3):
        strategy = strategy or self.meta["retriever"]
        if strategy == "dense":
            return self.store.similarity_search(q, k=k)
        if strategy == "mmr":
            return self.store.max_marginal_relevance_search(q, k=k, fetch_k=POOL, lambda_mult=0.6)
        if strategy == "bm25":
            return self._bm25(q, k)
        if strategy == "hybrid_rrf":
            return self._hybrid(q, k)
        if strategy == "hybrid_rerank":
            return self._rerank(q, self._hybrid(q, POOL), k)
        if strategy == "multiquery_rerank":
            variants = [q] + [v.strip(" -*0123456789.") for v in self.mq_chain.invoke({"question": q}).split("\n")
                              if v.strip()][:3]
            return self._rerank(q, rrf([self._hybrid(v, POOL) for v in variants])[:POOL], k)
        raise ValueError(f"unknown strategy {strategy}")

    # ---- conversation
    def condense(self, hist, question):
        if not hist:
            return question
        hist_txt = "\n".join(("User: " if isinstance(m, HumanMessage) else "Assistant: ") + m.content[:200]
                             for m in hist[-4:])
        try:
            raw = self.condense_chain.invoke({"history": hist_txt, "question": question})
        except Exception:
            raw = ""
        cand = next((l.strip(' "*-') for l in raw.splitlines() if l.strip()), "")
        cand = re.sub(r"^(standalone question|question|output)\s*:\s*", "", cand, flags=re.I)
        if 10 <= len(cand) <= 300 and cand.endswith("?") and not re.search(r"i don't know|based on the provided", cand, re.I):
            return cand
        last_q = next((m.content for m in reversed(hist) if isinstance(m, HumanMessage)), "")
        return f"{last_q} {question}".strip()

    def chat(self, session_id, question, strategy=None):
        hist = self.sessions.setdefault(session_id, [])
        standalone = self.condense(hist, question)
        docs = self.retrieve(standalone, strategy, 3)
        ans = self.answer_chain.invoke({"context": format_docs(docs), "chat_history": hist[-MAX_MSGS:],
                                        "question": question})
        hist += [HumanMessage(question), AIMessage(ans)]
        return {"answer": ans, "sources": sources_of(docs), "standalone_question": standalone}

    def reset(self, session_id):
        self.sessions.pop(session_id, None)
