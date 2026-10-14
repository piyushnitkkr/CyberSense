"""Streamlit chat UI for CyberSense."""

from __future__ import annotations

import json
import os
import uuid

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CyberSense — Cybersecurity RAG Chatbot",
    page_icon="🛡️",
    layout="wide",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_debug" not in st.session_state:
    st.session_state.last_debug = {}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    st.subheader("Source Filters")
    sources = st.multiselect(
        "Limit to sources",
        ["attack", "cwe", "capec", "nvd", "kev", "owasp", "nist", "upload"],
        default=[],
        help="Leave empty to search all sources.",
    )

    top_k = st.slider("Top-K results", min_value=3, max_value=15, value=8)
    reranker_on = st.checkbox("Enable reranker", value=True)

    st.divider()
    st.subheader("📄 Upload Document")
    uploaded = st.file_uploader(
        "Upload PDF / DOCX / MD / TXT / HTML",
        type=["pdf", "docx", "md", "txt", "html"],
    )
    if uploaded and st.button("Ingest document"):
        with st.spinner("Ingesting…"):
            resp = requests.post(
                f"{API_BASE}/api/v1/documents",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
            )
            if resp.ok:
                st.success(f"✅ Ingested: {resp.json()}")
            else:
                st.error(f"❌ {resp.text}")

    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
st.title("🛡️ CyberSense")
st.caption("Cybersecurity RAG Chatbot — answers grounded in indexed sources with citations.")

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            _render_citations(msg["citations"])

# Input
if prompt := st.chat_input("Ask a cybersecurity question…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_answer = ""
        citations = []
        debug_info = {}

        try:
            payload = {
                "message": prompt,
                "session_id": st.session_state.session_id,
                "stream": False,
                "filters": {
                    "sources": sources or None,
                    "top_k": top_k,
                },
            }
            with st.spinner("Retrieving and generating…"):
                resp = requests.post(f"{API_BASE}/api/v1/chat", json=payload, timeout=120)

            if resp.ok:
                data = resp.json()
                full_answer = data.get("answer", "")
                citations = data.get("citations", [])
                debug_info = {
                    "rewritten_query": data.get("rewritten_query"),
                    "latency_ms": data.get("latency_ms", {}),
                }
                placeholder.markdown(full_answer)
                _render_citations(citations)
            else:
                err = resp.json().get("detail", resp.text)
                placeholder.error(f"❌ {err}")
                full_answer = f"Error: {err}"

        except requests.exceptions.ConnectionError:
            placeholder.error("❌ Cannot connect to API. Is the backend running?")
            full_answer = "Connection error."

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_answer,
            "citations": citations,
        })
        st.session_state.last_debug = debug_info

    # Debug expander
    if st.session_state.last_debug:
        with st.expander("🔍 Debug", expanded=False):
            st.json(st.session_state.last_debug)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ **Disclaimer:** Answers are generated from indexed public sources. "
    "Always verify critical security decisions with primary sources. "
    "CyberSense may make mistakes."
)


def _render_citations(citations: list[dict]) -> None:
    if not citations:
        return
    st.markdown("**Sources:**")
    for c in citations:
        with st.expander(f"[{c['n']}] {c['title']} — {c['source'].upper()}", expanded=False):
            if c.get("section_path"):
                st.caption(f"📂 {c['section_path']}")
            if c.get("url"):
                st.markdown(f"🔗 [{c['url']}]({c['url']})")
            if c.get("snippet"):
                st.text(c["snippet"])
