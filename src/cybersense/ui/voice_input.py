"""
voice_input.py — Browser-based voice input with multilingual STT for CyberSense.

Uses the browser's built-in Web Speech API — zero server load, no audio sent to backend.
Works in Chrome and Edge. 30+ languages supported.

Usage in app.py:
    from cybersense.ui.voice_input import render_voice_input, voice_language_selector

    lang_code  = voice_language_selector()
    transcript = render_voice_input(lang=lang_code)
    if transcript:
        # populate chat input with transcript
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


# ── Language Registry ───────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES: dict[str, str] = {
    "🇺🇸  English (US)":         "en-US",
    "🇬🇧  English (UK)":         "en-GB",
    "🇮🇳  Hindi":                 "hi-IN",
    "🇮🇳  Tamil":                 "ta-IN",
    "🇮🇳  Telugu":                "te-IN",
    "🇮🇳  Bengali":               "bn-IN",
    "🇮🇳  Marathi":               "mr-IN",
    "🇮🇳  Gujarati":              "gu-IN",
    "🇮🇳  Kannada":               "kn-IN",
    "🇵🇰  Urdu":                  "ur-PK",
    "🇸🇦  Arabic":                "ar-SA",
    "🇨🇳  Chinese (Simplified)":  "zh-CN",
    "🇹🇼  Chinese (Traditional)": "zh-TW",
    "🇯🇵  Japanese":              "ja-JP",
    "🇰🇷  Korean":                "ko-KR",
    "🇪🇸  Spanish":               "es-ES",
    "🇫🇷  French":                "fr-FR",
    "🇩🇪  German":                "de-DE",
    "🇵🇹  Portuguese (Brazil)":   "pt-BR",
    "🇵🇹  Portuguese (Portugal)": "pt-PT",
    "🇷🇺  Russian":               "ru-RU",
    "🇮🇹  Italian":               "it-IT",
    "🇳🇱  Dutch":                 "nl-NL",
    "🇸🇪  Swedish":               "sv-SE",
    "🇵🇱  Polish":                "pl-PL",
    "🇹🇷  Turkish":               "tr-TR",
    "🇹🇭  Thai":                  "th-TH",
    "🇻🇳  Vietnamese":            "vi-VN",
    "🇮🇩  Indonesian":            "id-ID",
    "🇲🇾  Malay":                 "ms-MY",
    "🇵🇭  Filipino":              "fil-PH",
}

DEFAULT_LANGUAGE_NAME = "🇺🇸  English (US)"
DEFAULT_LANGUAGE_CODE = "en-US"


# ── HTML/JS Component ───────────────────────────────────────────────────────────

_VOICE_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif}}
  body{{background:transparent;display:flex;align-items:center;gap:10px;padding:2px 0}}
  #btn{{display:flex;align-items:center;gap:8px;padding:8px 20px;border-radius:24px;
        border:1.5px solid #00E5FF;background:#1E293B;color:#00E5FF;font-size:14px;
        font-weight:600;cursor:pointer;transition:all .2s;user-select:none}}
  #btn:hover{{background:#00E5FF;color:#0B0F19}}
  #btn.rec{{background:#FF5252;border-color:#FF5252;color:#fff;animation:pulse 1.2s infinite}}
  #btn.ok{{background:#00F5A0;border-color:#00F5A0;color:#0B0F19}}
  #btn:disabled{{opacity:.4;cursor:not-allowed}}
  @keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 rgba(255,82,82,.5)}}50%{{box-shadow:0 0 0 8px rgba(255,82,82,0)}}}}
  #st{{font-size:12px;color:#94A3B8;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .err{{color:#FF5252!important}}.ok2{{color:#00F5A0!important}}.inf{{color:#00E5FF!important}}
</style></head>
<body>
  <button id="btn" onclick="go()"><span id="ic">🎙️</span><span id="lb">Speak</span></button>
  <span id="st">Click to record — result appears in chat box</span>
<script>
  const LANG="{lang_code}";
  const SA=window.SpeechRecognition||window.webkitSpeechRecognition;
  let r=null,busy=false,fin="";
  if(!SA){{
    setS("⚠️ Use Chrome or Edge for voice input","err");
    document.getElementById("btn").disabled=true;
  }}else{{
    r=new SA();r.lang=LANG;r.continuous=false;r.interimResults=true;r.maxAlternatives=1;
    r.onstart=()=>{{busy=true;fin="";setB("rec","🔴","Stop");setS("🎤 Listening in "+LANG+"…","inf")}};
    r.onresult=(e)=>{{
      let iv="";fin="";
      for(let i=e.resultIndex;i<e.results.length;i++){{
        const t=e.results[i][0].transcript;
        e.results[i].isFinal?fin+=t:iv+=t;
      }}
      setS((fin||iv)?'"'+(fin||iv)+'"':"…","inf");
    }};
    r.onend=()=>{{
      busy=false;
      if(fin){{
        setB("ok","✅","Done");setS('✔ "'+fin+'"',"ok2");
        window.parent.postMessage({{type:"streamlit:setComponentValue",value:fin}},"*");
      }}else{{setB("","🎙️","Speak");setS("No speech detected — try again","err");}}
    }};
    r.onerror=(e)=>{{
      busy=false;
      const m={{"not-allowed":"🚫 Mic access denied","no-speech":"🔇 No speech detected",
               "network":"📡 Network error","audio-capture":"🎤 Mic not found"}};
      setB("","🎙️","Speak");setS(m[e.error]||"Error: "+e.error,"err");
    }};
  }}
  function go(){{if(!r)return;busy?r.stop():(r.lang=LANG,r.start());}}
  function setB(c,i,l){{document.getElementById("btn").className=c;
    document.getElementById("ic").textContent=i;document.getElementById("lb").textContent=l;}}
  function setS(m,c){{const s=document.getElementById("st");s.textContent=m;s.className=c;}}
</script></body></html>"""


def render_voice_input(lang: str = DEFAULT_LANGUAGE_CODE, key: str = "voice_btn") -> str | None:
    """
    Render the microphone button. Returns transcribed text string when user
    finishes speaking, or None while idle.

    Parameters
    ----------
    lang : BCP-47 tag e.g. 'en-US', 'hi-IN', 'zh-CN'
    key  : Unique Streamlit component key
    """
    result = components.html(
        _VOICE_HTML.format(lang_code=lang),
        height=46,
        scrolling=False,
        key=key,
    )
    return result if isinstance(result, str) and result.strip() else None


def voice_language_selector(label: str = "🌐 Speak in", key: str = "voice_lang") -> str:
    """Dropdown to pick voice language. Returns the BCP-47 code."""
    names = list(SUPPORTED_LANGUAGES.keys())
    display = st.selectbox(
        label,
        options=names,
        index=names.index(DEFAULT_LANGUAGE_NAME),
        key=key,
        help="Select the language you will speak in. Audio is processed locally by your browser — nothing is sent to CyberSense servers.",
    )
    return SUPPORTED_LANGUAGES[display]
