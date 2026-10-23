"""Streamlit UI for the Research Paper Answer Bot.  Run:  streamlit run app.py"""
import os, sys, uuid

# Streamlit Community Cloud ships an old sqlite3 that ChromaDB rejects; use the bundled one when available.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st
from local_models import get_groq_key
from rag_core import RAGEngine, STRATEGIES

st.set_page_config(page_title="Research Paper Answer Bot", page_icon=":page_facing_up:", layout="wide")
st.title("Research Paper Answer Bot")
st.caption("RAG over your paper collection: local ChromaDB + retrieval strategies, answers generated via Groq. "
           "Every answer shows its top-3 supporting passages with paper title and page.")


# API key: env var / Streamlit secrets (deployed) first; otherwise ask the visitor (kept only in this server session).
if not get_groq_key():
    typed = st.sidebar.text_input("Groq API key", type="password", help="Get one at console.groq.com/keys")
    if typed:
        os.environ["GROQ_API_KEY"] = typed.strip()
        st.rerun()
    st.info("Enter your Groq API key in the sidebar (or set GROQ_API_KEY / a Streamlit secret) to start.")
    st.stop()


@st.cache_resource(show_spinner="Loading index and embedder (first run only)...")
def get_engine():
    return RAGEngine()


try:
    engine = get_engine()
except Exception as e:
    st.error(f"Could not start the RAG engine: {e}")
    st.info("Run the notebook through Section 5 first (it saves artifacts/), check that GROQ_API_KEY is valid, then reload.")
    st.stop()

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:8]
    st.session_state.messages = []


def show_sources(sources):
    with st.expander("Top-3 sources", expanded=False):
        for s in sources:
            st.markdown(f"**[{s['rank']}] {s['paper_title']}**, page {s['page']}  \n`{s['source']}`")
            st.caption(s["snippet"])


with st.sidebar:
    st.header("Settings")
    strategy = st.selectbox("Retrieval strategy", STRATEGIES,
                            index=STRATEGIES.index(engine.meta["retriever"]),
                            help="The notebook's evaluation picked the default.")
    st.write(f"Session: `{st.session_state.session_id}`")
    if st.button("New chat"):
        engine.reset(st.session_state.session_id)
        st.session_state.session_id = uuid.uuid4().hex[:8]
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.json(engine.info())

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            show_sources(m["sources"])

if prompt := st.chat_input("Ask a question about the papers"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving and generating..."):
            out = engine.chat(st.session_state.session_id, prompt, strategy)
        st.markdown(out["answer"])
        if out["standalone_question"] != prompt:
            st.caption(f"Searched as: {out['standalone_question']}")
        show_sources(out["sources"])
    st.session_state.messages.append({"role": "assistant", "content": out["answer"], "sources": out["sources"]})
