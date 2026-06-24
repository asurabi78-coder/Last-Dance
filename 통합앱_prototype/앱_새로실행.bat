@echo off
cd /d "%~dp0"
rmdir /s /q core\__pycache__ 2>nul
rmdir /s /q __pycache__ 2>nul
".venv\Scripts\python.exe" -m streamlit run app.py
