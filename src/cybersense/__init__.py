"""CyberSense — Cybersecurity RAG Chatbot."""

import os
from pathlib import Path

__version__ = "0.1.0"

_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(_ROOT / ".hf_cache"))
os.environ.setdefault("TORCH_HOME", str(_ROOT / ".torch_cache"))
