"""
voice_input.py — Browser-based voice input with multilingual STT for CyberSense.

USAGE in app.py:
    from cybersense.ui.voice_input import render_voice_input, voice_language_selector

    lang_code = voice_language_selector()           # language picker dropdown
    transcript = render_voice_input(lang=lang_code) # returns spoken text or None

HOW IT WORKS:
    - Injects a small self-contained HTML+JS snippet via st.components.v1.html()
    - Uses the browser's built-in Web Speech API (SpeechRecognition) — zero server load
    - Interim results shown as user speaks; final transcript posted back to Streamlit
    - Works in Chrome / Edge (full support) and Firefox (partial)
    - Falls back gracefully with a clear error message in unsupported browsers

SUPPORTED LANGUAGES: 30 languages including English, Hindi, Arabic, Chinese,
Spanish, French, German, Japanese, Korean, Portuguese, Tamil, Telugu, Bengali,
Marathi, Gujarati, Urdu, Russian, Italian, Dutch, Turkish, Thai, Vietnamese, ...
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


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


# ── Voice Button Component ──────────────────────────────────────────────────────

_VOICE_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  :root {{
    --accent: #00E5FF;  --panel:  #1E293B;
    --text:   #F1F5F9;  --muted:  #94A3B8;
    --green:  #00F5A0;  --red:    #FF5252;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0;
       font-family: 'Segoe UI', system-ui, sans-serif; }}
  body {{ background: transparent; display: flex; align-items: center;
          gap: 10px; padding: 2px 0; }}

  #voiceBtn {{
    display: flex; align-items: center; gap: 8px;
    padding: 8px 20px; border-radius: 24px;
    border: 1.5px solid var(--accent);
    background: var(--panel); color: var(--accent);
    font-size: 14px; font-weight: 600; cursor: pointer;
    transition: all 0.2s ease; user-select: none;
  }}
  #voiceBtn:hover  {{ background: var(--accent); color: #0B0F19; }}
  #voiceBtn.active {{
    background: var(--red); border-color: var(--red); color: #fff;
    animation: pulse 1.2s infinite;
  }}
  #voiceBtn.done   {{ background: var(--green); border-color: var(--green); color: #0B0F19; }}
  #voiceBtn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

  @keyframes pulse {{
    0%,100% {{ box-shadow: 0 0 0 0 rgba(255,82,82,.5); }}
    50%     {{ box-shadow: 0 0 0 8px rgba(255,82,82,0); }}
  }}

  #statusText {{
    font-size: 12px; color: var(--muted); max-width: 280px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  .err  {{ color: var(--red)   !important; }}
  .ok   {{ color: var(--green) !important; }}
  .info {{ color: var(--accent)!important; }}
</style>
</head>
<body>
  <button id="voiceBtn" onclick="toggle()">
    <span id="icon">🎙️</span>
    <span id="label">Speak</span>
  </button>
  <span id="statusText">Click to record — results appear in chat box</span>

<script>
  const LANG = "{lang_code}";
  const SA   = window.SpeechRecognition || window.webkitSpeechRecognition;
  let rec = null, busy = false, final = "";

  if (!SA) {{
    setStatus("⚠️ Speech API not available — use Chrome or Edge", "err");
    document.getElementById("voiceBtn").disabled = true;
  }} else {{
    rec = new SA();
    rec.lang = LANG;
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {{
      busy = true; final = "";
      setBtn("active","🔴","Stop");
      setStatus("🎤 Listening in " + LANG + " ...", "info");
    }};

    rec.onresult = (e) => {{
      let interim = "";
      final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {{
        const t = e.results[i][0].transcript;
        e.results[i].isFinal ? final += t : interim += t;
      }}
      setStatus((final || interim) ? "\\"" + (final||interim) + "\\"" : "...", "info");
    }};

    rec.onend = () => {{
      busy = false;
      if (final) {{
        setBtn("done","✅","Use text");
        setStatus("✔ \\"" + final + "\\"", "ok");
        // Send to Streamlit parent frame
        window.parent.postMessage({{
          type: "streamlit:setComponentValue",
          value: final
        }}, "*");
      }} else {{
        setBtn("","🎙️","Speak");
        setStatus("No speech detected — try again", "err");
      }}
    }};

    rec.onerror = (e) => {{
      busy = false;
      const msgs = {{
        "not-allowed":   "🚫 Microphone access denied — allow mic in browser settings",
        "no-speech":     "🔇 No speech detected",
        "network":       "📡 Network error",
        "audio-capture": "🎤 Microphone not found",
      }};
      setBtn("","🎙️","Speak");
      setStatus(msgs[e.error] || "Error: "+e.error, "err");
    }};
  }}

  function toggle() {{
    if (!rec) return;
    if (busy) {{ rec.stop(); }}
    else      {{ rec.lang = LANG; rec.start(); }}
  }}

  function setBtn(cls, icon, lbl) {{
    const b = document.getElementById("voiceBtn");
    b.className = cls;
    document.getElementById("icon").textContent  = icon;
    document.getElementById("label").textContent = lbl;
  }}

  function setStatus(msg, cls) {{
    const s = document.getElementById("statusText");
    s.textContent = msg;
    s.className   = cls;
  }}
</script>
</body>
</html>
"""


def render_voice_input(lang: str = DEFAULT_LANGUAGE_CODE, key: str = "voice_btn") -> str | None:
    """
    Render the microphone button component.

    Returns the transcribed text string once the user finishes speaking,
    or None while idle / between recordings.

    Parameters
    ----------
    lang : BCP-47 language tag, e.g. 'en-US', 'hi-IN', 'zh-CN'.
    key  : Unique Streamlit component key.
    """
    result = components.html(
        _VOICE_HTML.format(lang_code=lang),
        height=46,
        scrolling=False,
        key=key,
    )
    # components.html returns None by default; it returns the postMessage value
    # when Streamlit's bidirectional component protocol receives it.
    return result if isinstance(result, str) and result.strip() else None


def voice_language_selector(
    label: str = "🌐 Input Language",
    key: str = "voice_lang",
) -> str:
    """
    Render a compact language selector. Returns the BCP-47 code for the chosen language.
    """
    idx = list(SUPPORTED_LANGUAGES.keys()).index(DEFAULT_LANGUAGE_NAME)
    display = st.selectbox(
        label,
        options=list(SUPPORTED_LANGUAGES.keys()),
        index=idx,
        key=key,
        help=(
            "Select the language you will speak in. "
            "The browser's Speech Recognition engine processes audio locally — "
            "no audio is sent to CyberSense servers."
        ),
    )
    return SUPPORTED_LANGUAGES[display]
