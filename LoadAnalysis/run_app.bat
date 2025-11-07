@echo off
echo Starting TMS Lane & Rate Analysis Dashboard...
cd /d %~dp0
C:\Python314\python.exe -m streamlit run app.py
pause

