#!/usr/bin/env python3
"""Standalone Streamlit app for LiveX Chat Agent."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the Streamlit app
from livex_chat_agent.ui.streamlit_app import main

if __name__ == "__main__":
    main()
