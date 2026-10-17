"""Streamlit chat UI for CyberSense."""

from __future__ import annotations

import json
import os
import uuid

import requests
import streamlit as st

def _get_default_api_base() -> str:
    env_val = os.getenv("API_BASE_URL", "")
    if env_val:
        return env_val.rstrip("/")
    try:
        if hasattr(st, "secrets") and "API_BASE_URL" in st.secrets:
            return str(st.secrets["API_BASE_URL"]).rstrip("/")
    except Exception:
        pass
    # Default to live Render backend for cloud deployment
    return "https://cybersense-api-vorj.onrender.com"

st.set_page_config(
    page_title="CyberSense — Cybersecurity RAG Chatbot",
    page_icon="🛡️",
    layout="wide",
)


# ── Helper functions (must be defined before use) ─────────────────────────────

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


def _send_feedback(message_id: str, rating: str, api_base: str = "") -> bool:
    try:
        base = api_base or API_BASE
        resp = requests.post(
            f"{base}/api/v1/feedback",
            json={"message_id": message_id, "rating": rating},
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


# ── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_base" not in st.session_state:
    st.session_state.api_base = _get_default_api_base()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    with st.expander("🌐 Backend Connection", expanded=False):
        api_input = st.text_input(
            "Backend API URL",
            value=st.session_state.api_base,
            help="URL of the CyberSense FastAPI backend (e.g. https://cybersense-api.onrender.com)",
        )
        st.session_state.api_base = api_input.rstrip("/")
        if st.button("Test Connection", key="btn_test_conn"):
            with st.spinner("Connecting to backend (Render may take ~20s to wake up)..."):
                try:
                    r = requests.get(f"{st.session_state.api_base}/health", timeout=30)
                    if r.ok:
                        data = r.json()
                        api_chk = data.get("checks", {}).get("api", "ok")
                        qd_chk = data.get("checks", {}).get("qdrant", "ok")
                        st.success(f"✅ Connected! API: {api_chk} | Qdrant: {qd_chk}")
                    else:
                        st.warning(f"Returned status {r.status_code}")
                except Exception as e:
                    st.error(f"Cannot connect: {e}")

    API_BASE = st.session_state.api_base

    st.subheader("Source Filters")
    sources = st.multiselect(
        "Limit to sources",
        ["attack", "cwe", "capec", "nvd", "kev", "owasp", "nist", "upload"],
        default=[],
        help="Leave empty to search all sources.",
    )

    top_k = st.slider("Top-K results", min_value=3, max_value=15, value=8)
    reranker_on = st.checkbox("Enable cross-encoder reranker", value=False, help="Disabled by default on free-tier deployments to save RAM.")

    st.divider()
    st.subheader("📄 Upload Document")
    uploaded = st.file_uploader(
        "Upload PDF / DOCX / MD / TXT / HTML",
        type=["pdf", "docx", "md", "txt", "html"],
    )
    if uploaded and st.button("Ingest document", key="btn_ingest"):
        with st.spinner("Ingesting and indexing document…"):
            try:
                content_type = uploaded.type or "application/octet-stream"
                resp = requests.post(
                    f"{API_BASE}/api/v1/documents",
                    files={"file": (uploaded.name, uploaded.getvalue(), content_type)},
                    timeout=120,
                )
                if resp.ok:
                    data = resp.json()
                    title = data.get("title", uploaded.name)
                    doc_id = data.get("doc_ids", [""])[0]
                    st.success(f"✅ Ingested successfully!\n\n**Document:** {title}\n\n**ID:** `{doc_id}`")
                else:
                    try:
                        err = resp.json().get("detail", resp.text)
                    except Exception:
                        err = resp.text[:300]
                    st.error(f"❌ {err}")
            except requests.exceptions.Timeout:
                st.error("❌ Ingestion timed out. The backend took too long to process the document.")
            except requests.exceptions.ConnectionError:
                st.error(f"❌ Cannot connect to backend at {API_BASE}. Please verify the Backend API URL.")
            except Exception as exc:
                st.error(f"❌ Upload failed: {exc}")

    st.divider()
    if st.button("🗑️ Clear chat", key="btn_clear"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.last_debug = {}
        st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
st.title("🛡️ CyberSense")
st.caption("Cybersecurity RAG Chatbot — answers grounded in indexed sources with citations.")

# Render history
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("citations"):
                _render_citations(msg["citations"])
            # Thumbs feedback
            msg_id = msg.get("message_id", "")
            if msg_id:
                col1, col2, _ = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍", key=f"up_{idx}"):
                        _send_feedback(msg_id, "up")
                        st.toast("Thanks for your feedback!")
                with col2:
                    if st.button("👎", key=f"dn_{idx}"):
                        _send_feedback(msg_id, "down")
                        st.toast("Thanks for your feedback!")

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
        message_id = ""

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
                message_id = data.get("message_id", "")
                placeholder.markdown(full_answer)
                _render_citations(citations)
            else:
                try:
                    data = resp.json()
                    err = data.get("detail", str(data))
                except Exception:
                    if resp.status_code in (502, 503, 504) or resp.text.strip().startswith("<"):
                        err = f"Backend service is temporarily unavailable or restarting (HTTP {resp.status_code}). Please try again in 15-20 seconds."
                    else:
                        err = resp.text[:300]
                placeholder.error(f"❌ {err}")
                full_answer = f"Error: {err}"

        except requests.exceptions.Timeout:
            err_msg = "Request timed out waiting for backend. On Render free tier, the first request may take ~30s to wake up."
            placeholder.error(f"❌ {err_msg}")
            full_answer = err_msg
        except requests.exceptions.ConnectionError:
            err_msg = "Cannot connect to API. Is the backend URL correct and the service running?"
            placeholder.error(f"❌ {err_msg}")
            full_answer = err_msg

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_answer,
            "citations": citations,
            "message_id": message_id,
        })



# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ **Disclaimer:** Answers are generated from indexed public sources. "
    "Always verify critical security decisions with primary sources. "
    "CyberSense may make mistakes."
)
