"""
app.py (updated) — CyberSense Streamlit Chat UI with Voice Input + Multilingual STT.

Changes from previous version:
  1. Import voice_input module
  2. Add voice language selector in sidebar
  3. Add microphone button below the chat input
  4. Auto-populate chat input when voice transcript is received
  5. Translate non-English queries to English before hitting the API
     (uses googletrans, falls back gracefully if unavailable)

INSTALL additional deps:
    pip install googletrans==4.0.0rc1    # optional: for query translation
    # No extra deps needed for browser STT — it's built into Chrome/Edge
"""

import asyncio
import json
import time
from typing import Generator

import httpx
import streamlit as st

# Voice input module (copy voice_input.py to src/cybersense/ui/)
from cybersense.ui.voice_input import (
    DEFAULT_LANGUAGE_CODE,
    render_voice_input,
    voice_language_selector,
)

# ── Optional translation support ────────────────────────────────────────────────
try:
    from googletrans import Translator
    _translator = Translator()
    TRANSLATION_AVAILABLE = True
except ImportError:
    _translator = None
    TRANSLATION_AVAILABLE = False


# ── Config ──────────────────────────────────────────────────────────────────────
API_BASE = st.secrets.get("API_BASE_URL", "https://cybersense-api-vorj.onrender.com")
CHAT_ENDPOINT = f"{API_BASE}/api/v1/chat"


# ── Page Setup ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberSense",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""
if "voice_lang" not in st.session_state:
    st.session_state.voice_lang = DEFAULT_LANGUAGE_CODE


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ CyberSense")
    st.caption("AI-powered cybersecurity knowledge assistant")
    st.divider()

    # --- Source filter ---
    st.markdown("**📚 Data Sources**")
    source_attack  = st.checkbox("MITRE ATT&CK",  value=True)
    source_cwe     = st.checkbox("MITRE CWE",      value=True)
    source_owasp   = st.checkbox("OWASP Top 10",   value=True)
    source_docs    = st.checkbox("Custom Docs",     value=True)

    enabled_sources = []
    if source_attack: enabled_sources.append("attack")
    if source_cwe:    enabled_sources.append("cwe")
    if source_owasp:  enabled_sources.append("owasp")
    if source_docs:   enabled_sources.append("user_docs")

    st.divider()

    # --- Voice language selector ---
    st.markdown("**🎙️ Voice Input Settings**")
    selected_lang = voice_language_selector(
        label="Speak in...",
        key="sidebar_voice_lang",
    )
    st.session_state.voice_lang = selected_lang

    if selected_lang != "en-US" and TRANSLATION_AVAILABLE:
        st.info(
            "🌐 Your voice input will be **auto-translated to English** "
            "before querying CyberSense.",
            icon="ℹ️",
        )
    elif selected_lang != "en-US" and not TRANSLATION_AVAILABLE:
        st.warning(
            "googletrans not installed — query will be sent as-is. "
            "Install with: `pip install googletrans==4.0.0rc1`",
            icon="⚠️",
        )

    st.divider()

    # --- Conversation controls ---
    st.markdown("**⚙️ Controls**")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.voice_transcript = ""
        st.rerun()

    # --- API health ---
    st.divider()
    st.markdown("**🔌 API Status**")
    if st.button("Check health", use_container_width=True):
        try:
            r = httpx.get(f"{API_BASE}/health", timeout=5)
            if r.status_code == 200:
                st.success("API: Online ✅")
            else:
                st.error(f"API: HTTP {r.status_code}")
        except Exception as e:
            st.error(f"API: Unreachable — {e}")


# ── Helper: translate query to English ─────────────────────────────────────────

def maybe_translate(text: str, source_lang: str) -> tuple[str, str | None]:
    """
    If source_lang is not English and googletrans is available,
    translate text to English.

    Returns (translated_text, original_text_or_None).
    """
    if source_lang.startswith("en") or not TRANSLATION_AVAILABLE or not _translator:
        return text, None
    try:
        result = _translator.translate(text, src=source_lang.split("-")[0], dest="en")
        translated = result.text
        if translated and translated.lower() != text.lower():
            return translated, text
        return text, None
    except Exception:
        return text, None


# ── Helper: stream chat response ────────────────────────────────────────────────

def stream_chat(query: str, conv_id: str | None, sources: list[str]) -> Generator[str, None, None]:
    payload = {
        "query": query,
        "conversation_id": conv_id,
        "source_filter": sources if sources else None,
        "stream": True,
    }
    with httpx.stream(
        "POST", CHAT_ENDPOINT, json=payload,
        headers={"Accept": "text/event-stream"},
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    if "delta" in chunk:
                        yield chunk["delta"]
                    elif "conversation_id" in chunk:
                        st.session_state.conversation_id = chunk["conversation_id"]
                except json.JSONDecodeError:
                    yield data


# ── Main Chat UI ────────────────────────────────────────────────────────────────

st.markdown("## 🛡️ CyberSense — Cybersecurity AI Assistant")
st.caption(
    "Ask anything about MITRE ATT&CK techniques, CWE weaknesses, OWASP risks, "
    "or upload your own security documents."
)

# --- Render chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Voice Input Section ─────────────────────────────────────────────────────────

voice_col, text_col = st.columns([1, 5], gap="small")

with voice_col:
    st.markdown("**🎙️ Voice**")
    voice_result = render_voice_input(
        lang=st.session_state.voice_lang,
        key="main_voice_btn",
    )
    # If browser returned a transcript via postMessage → prefill the state
    if voice_result:
        st.session_state.voice_transcript = voice_result

with text_col:
    # Show voice transcript preview if captured
    if st.session_state.voice_transcript:
        st.info(f"🎙️ Heard: **{st.session_state.voice_transcript}**  — press Send or edit below.")

# --- Chat input (pre-populated with voice transcript if any) ---
prefill = st.session_state.voice_transcript or ""
user_input = st.chat_input(
    placeholder="Ask a cybersecurity question (or use voice above)…",
    key="chat_input_box",
)

# If user typed something, that takes priority over voice transcript
query = user_input or (st.session_state.voice_transcript if not user_input else "")

if query and query.strip():
    # Clear voice transcript after use
    st.session_state.voice_transcript = ""

    # --- Translate if needed ---
    translated_query, original_query = maybe_translate(
        query.strip(), st.session_state.voice_lang
    )

    # Build display text (show original in a note if translated)
    display_query = query.strip()
    if original_query:
        display_query = f"{original_query}\n\n*(Translated: {translated_query})*"

    # Append user message
    st.session_state.messages.append({"role": "user", "content": display_query})
    with st.chat_message("user"):
        st.markdown(display_query)

    # --- Stream assistant response ---
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        try:
            for chunk in stream_chat(
                translated_query,
                st.session_state.conversation_id,
                enabled_sources,
            ):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
        except httpx.HTTPStatusError as e:
            full_response = f"❌ API error ({e.response.status_code}): {e.response.text}"
            response_placeholder.error(full_response)
        except Exception as e:
            full_response = f"❌ Connection error: {str(e)}"
            response_placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
