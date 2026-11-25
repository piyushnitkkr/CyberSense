"""
app.py — CyberSense Streamlit Chat UI with Voice Input + Multilingual STT.
"""

from __future__ import annotations

import json
from typing import Generator

import httpx
import streamlit as st

# Voice input — browser-based, zero server load
from cybersense.ui.voice_input import (
    DEFAULT_LANGUAGE_CODE,
    render_voice_input,
    voice_language_selector,
)

# Optional translation (non-English → English before RAG query)
try:
    from deep_translator import GoogleTranslator as _GoogleTranslator
    TRANSLATION_AVAILABLE = True
except Exception:
    _GoogleTranslator = None  # type: ignore[assignment,misc]
    TRANSLATION_AVAILABLE = False


# ── Config ──────────────────────────────────────────────────────────────────────

API_BASE = st.secrets.get("API_BASE_URL", "https://cybersense-api-vorj.onrender.com")
CHAT_ENDPOINT = f"{API_BASE}/api/v1/chat"


# ── Page config ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CyberSense",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Session state ────────────────────────────────────────────────────────────────

for _k, _v in {
    "messages": [],
    "conversation_id": None,
    "voice_transcript": "",
    "voice_lang": DEFAULT_LANGUAGE_CODE,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Sidebar ──────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛡️ CyberSense")
    st.caption("AI-powered cybersecurity knowledge assistant")
    st.divider()

    # Data source toggles
    st.markdown("**📚 Data Sources**")
    enabled_sources: list[str] = []
    if st.checkbox("MITRE ATT&CK",  value=True): enabled_sources.append("attack")
    if st.checkbox("MITRE CWE",      value=True): enabled_sources.append("cwe")
    if st.checkbox("OWASP Top 10",   value=True): enabled_sources.append("owasp")
    if st.checkbox("Custom Docs",    value=True): enabled_sources.append("user_docs")

    st.divider()

    # Voice language selector
    st.markdown("**🎙️ Voice Input**")
    selected_lang = voice_language_selector(label="Speak in", key="sidebar_voice_lang")
    st.session_state.voice_lang = selected_lang

    if selected_lang != "en-US":
        if TRANSLATION_AVAILABLE:
            st.info(
                "🌐 Non-English voice input will be **auto-translated to English** before querying.",
                icon="ℹ️",
            )
        else:
            st.warning(
                "Install `deep-translator>=1.11.4` for auto-translation of non-English speech.",
                icon="⚠️",
            )

    st.divider()

    # Controls
    st.markdown("**⚙️ Controls**")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.voice_transcript = ""
        st.rerun()

    # Health check
    st.divider()
    st.markdown("**🔌 API Status**")
    if st.button("Check health", use_container_width=True):
        try:
            r = httpx.get(f"{API_BASE}/health", timeout=5)
            st.success("API: Online ✅") if r.status_code == 200 else st.error(f"API: HTTP {r.status_code}")
        except Exception as e:
            st.error(f"API: Unreachable — {e}")


# ── Helpers ──────────────────────────────────────────────────────────────────────

def maybe_translate(text: str, source_lang: str) -> tuple[str, str | None]:
    """Translate text to English if needed. Returns (translated, original_or_None)."""
    if source_lang.startswith("en") or not TRANSLATION_AVAILABLE or _GoogleTranslator is None:
        return text, None
    try:
        src = source_lang.split("-")[0]  # e.g. 'hi' from 'hi-IN'
        translated = _GoogleTranslator(source=src, target="en").translate(text)
        return (translated, text) if translated and translated.lower() != text.lower() else (text, None)
    except Exception:
        return text, None


def stream_chat(
    query: str,
    conv_id: str | None,
    sources: list[str],
) -> Generator[str, None, None]:
    """Stream a chat response from the CyberSense API via SSE."""
    payload = {
        "message": query,
        "session_id": conv_id,
        "source_filter": sources or None,
        "stream": True,
    }
    with httpx.stream(
        "POST",
        CHAT_ENDPOINT,
        json=payload,
        headers={"Accept": "text/event-stream"},
        timeout=60,
    ) as resp:
        # Read error body before raise_for_status so .text is available
        if resp.status_code >= 400:
            resp.read()
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    # Token stream: {"token": "..."}
                    if "token" in chunk:
                        yield chunk["token"]
                    # Final summary frame: {"done": true, "session_id": "...", ...}
                    if chunk.get("done") and "session_id" in chunk:
                        st.session_state.conversation_id = chunk["session_id"]
                except json.JSONDecodeError:
                    yield data


# ── Main UI ──────────────────────────────────────────────────────────────────────

st.markdown("## 🛡️ CyberSense — Cybersecurity AI Assistant")
st.caption(
    "Ask anything about MITRE ATT&CK techniques, CWE weaknesses, OWASP risks, "
    "or upload your own security documents."
)

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Voice input row ───────────────────────────────────────────────────────────────

voice_col, info_col = st.columns([2, 4], gap="small")

with voice_col:
    voice_result = render_voice_input(
        lang=st.session_state.voice_lang,
        key="main_voice_btn",
    )
    if voice_result:
        st.session_state.voice_transcript = voice_result

with info_col:
    if st.session_state.voice_transcript:
        st.info(f'🎙️ Heard: **"{st.session_state.voice_transcript}"**')

# ── Chat input ────────────────────────────────────────────────────────────────────

user_input = st.chat_input("Ask a cybersecurity question (or use voice above)…")

# Prefer typed input; fall back to voice transcript
query_raw = user_input or st.session_state.voice_transcript

if query_raw and query_raw.strip():
    st.session_state.voice_transcript = ""  # clear after use

    translated, original = maybe_translate(query_raw.strip(), st.session_state.voice_lang)

    display_text = (
        f"{original}\n\n*(Auto-translated: {translated})*" if original else query_raw.strip()
    )

    # Append + display user message
    st.session_state.messages.append({"role": "user", "content": display_text})
    with st.chat_message("user"):
        st.markdown(display_text)

    # Stream assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        try:
            for chunk in stream_chat(translated, st.session_state.conversation_id, enabled_sources):
                full_response += chunk
                placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.text
            except Exception:
                detail = str(e)
            full_response = f"❌ API error ({e.response.status_code}): {detail}"
            placeholder.error(full_response)
        except Exception as e:
            full_response = f"❌ Connection error: {e}"
            placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()
