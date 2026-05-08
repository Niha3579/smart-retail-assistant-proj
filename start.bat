@echo off
echo Smart Retail Assistant — Starting up...
echo.

REM Step 1: Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt -q

REM Step 2: Init DB and load data
echo [2/3] Initializing database and loading dataset...
python init_db.py

REM Step 3: Start Flask server
echo [3/3] Starting Flask server...
echo.
echo Open in browser: http://127.0.0.1:5000
echo Admin portal:    http://127.0.0.1:5000/admin
echo.
set FLASK_APP=run.py
python -m flask run
