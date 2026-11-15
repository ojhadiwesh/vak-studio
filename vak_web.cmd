@echo off
rem Vak web app: library, learning player, create a chant film. Opens http://127.0.0.1:8787
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m web %*
