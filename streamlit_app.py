"""
streamlit_app.py — Entry point for Streamlit Community Cloud.
Imports and runs the CyberSense chat UI.

Streamlit Community Cloud looks for this file in the root of the repo.
It re-exports the UI from src/cybersense/ui/app.py via sys.path manipulation.
"""

import os
import runpy
import sys

# Add src to Python path so cybersense package can be found
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Execute the UI module on every Streamlit rerun
app_path = os.path.join(src_path, "cybersense", "ui", "app.py")
runpy.run_path(app_path, run_name="__main__")
