"""
voice_input.py — Multilingual voice input for CyberSense using Streamlit's native
st.audio_input and SpeechRecognition (30+ languages).
"""

from __future__ import annotations

import io
import speech_recognition as sr
import streamlit as st


# ── Language Registry ───────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES: dict[str, str] = {
    "🇺🇸  English (US)":          "en-US",
    "🇬🇧  English (UK)":          "en-GB",
    "🇮🇳  Hindi":                  "hi-IN",
    "🇮🇳  Tamil":                  "ta-IN",
    "🇮🇳  Telugu":                 "te-IN",
    "🇮🇳  Bengali":                "bn-IN",
    "🇮🇳  Marathi":                "mr-IN",
    "🇮🇳  Gujarati":               "gu-IN",
    "🇮🇳  Kannada":                "kn-IN",
    "🇵🇰  Urdu":                   "ur-PK",
    "🇸🇦  Arabic":                 "ar-SA",
    "🇨🇳  Chinese (Simplified)":   "zh-CN",
    "🇹🇼  Chinese (Traditional)":  "zh-TW",
    "🇯🇵  Japanese":               "ja-JP",
    "🇰🇷  Korean":                 "ko-KR",
    "🇪🇸  Spanish":                "es-ES",
    "🇫🇷  French":                 "fr-FR",
    "🇩🇪  German":                 "de-DE",
    "🇵🇹  Portuguese (Brazil)":    "pt-BR",
    "🇵🇹  Portuguese (Portugal)":  "pt-PT",
    "🇷🇺  Russian":                "ru-RU",
    "🇮🇹  Italian":                "it-IT",
    "🇳🇱  Dutch":                  "nl-NL",
    "🇸🇪  Swedish":                "sv-SE",
    "🇵🇱  Polish":                 "pl-PL",
    "🇹🇷  Turkish":                "tr-TR",
    "🇹🇭  Thai":                   "th-TH",
    "🇻🇳  Vietnamese":             "vi-VN",
    "🇮🇩  Indonesian":             "id-ID",
    "🇲🇾  Malay":                  "ms-MY",
    "🇵🇭  Filipino":               "fil-PH",
}

DEFAULT_LANGUAGE_NAME = "🇺🇸  English (US)"
DEFAULT_LANGUAGE_CODE = "en-US"


def voice_language_selector(label: str = "🌐 Speak in", key: str = "voice_lang_select") -> str:
    """Dropdown to pick voice language. Returns the BCP-47 language code."""
    names = list(SUPPORTED_LANGUAGES.keys())
    display = st.selectbox(
        label,
        options=names,
        index=names.index(DEFAULT_LANGUAGE_NAME),
        key=key,
        help="Select the language you will speak in. Non-English queries are auto-translated to English.",
    )
    return SUPPORTED_LANGUAGES[display]


def transcribe_audio_bytes(audio_bytes: bytes, lang: str = DEFAULT_LANGUAGE_CODE) -> str:
    """Transcribe WAV audio bytes using Google Web Speech API via SpeechRecognition."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data, language=lang)


def render_voice_input(lang: str = DEFAULT_LANGUAGE_CODE, key: str = "voice_audio_input") -> str | None:
    """
    Render Streamlit's native microphone recorder and return the transcribed text
    when a new recording is submitted, or None otherwise.
    """
    audio_file = st.audio_input("🎙️ Record your question", key=key)
    if audio_file is None:
        return None

    audio_bytes = audio_file.getvalue()
    # Prevent re-transcribing the exact same recording across Streamlit reruns
    audio_hash = hash(audio_bytes)
    last_hash_key = f"{key}_last_hash"
    if st.session_state.get(last_hash_key) == audio_hash:
        return None

    st.session_state[last_hash_key] = audio_hash
    with st.spinner(f"Transcribing ({lang})..."):
        try:
            text = transcribe_audio_bytes(audio_bytes, lang=lang)
            return text.strip() if text else None
        except sr.UnknownValueError:
            st.warning("🔇 Could not understand the audio. Please try speaking more clearly.")
            return None
        except sr.RequestError as exc:
            st.error(f"📡 Speech recognition service error: {exc}")
            return None
        except Exception as exc:
            st.error(f"🎙️ Audio processing error: {exc}")
            return None
