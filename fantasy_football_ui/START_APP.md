# How to Start the Fantasy Football Dashboard

## Quick Start

### Option 1: Using the Batch File (Windows)
1. Navigate to: `C:\Cursor\fantasy_football_ui`
2. Double-click: `run_app.bat`
3. The app will open in your browser automatically

### Option 2: Using Command Line
1. Open PowerShell or Command Prompt
2. Run these commands:
```powershell
cd C:\Cursor\fantasy_football_ui
py -m streamlit run app.py --server.port 8502
```

### Option 3: From Anywhere
```powershell
cd C:\Cursor
$env:PYTHONPATH="C:\Cursor"
py -m streamlit run fantasy_football_ui/app.py --server.port 8502
```

## Access the App

Once started, open your browser and go to:

**http://localhost:8502**

## If Port 8502 is Busy

The app will automatically use the next available port (8503, 8504, etc.)
Check the terminal output to see which port it's using.

## Stop the App

Press `Ctrl+C` in the terminal where it's running, or close the terminal window.

