import asyncio
import pandas as pd
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json

app = FastAPI()

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRADES_FILE = "trades.csv"
HOUSEHOLD_STATE_FILE = "household_state.json"

# Helper to get all trades from CSV
def get_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    df = pd.read_csv(TRADES_FILE)
    return df.to_dict(orient="records")

def get_household_state():
    if not os.path.exists(HOUSEHOLD_STATE_FILE):
        return {"households": {}, "hour": None}
    with open(HOUSEHOLD_STATE_FILE, "r") as f:
        return json.load(f)

# Helper to get simulation state (now includes household state and trades)
def get_simulation_state():
    trades = get_trades()
    household_state = get_household_state()
    return {"trades": trades, "household_state": household_state}

# Metrics calculation endpoint
@app.get("/metrics")
def get_latest_metrics():
    """Returns the latest metrics from the simulation"""
    if not os.path.exists(HOUSEHOLD_STATE_FILE):
        return JSONResponse(content={"error": "Simulation data not found."}, status_code=404)
    
    with open(HOUSEHOLD_STATE_FILE, "r") as f:
        try:
            log_data = json.load(f)
            if not log_data:
                return JSONResponse(content={"error": "No simulation data available yet."}, status_code=404)
            
            latest_entry = log_data[-1]
            metrics = latest_entry.get("metrics", {})
            return JSONResponse(content=metrics)
            
        except (json.JSONDecodeError, IndexError):
            return JSONResponse(content={"error": "Invalid simulation data format."}, status_code=500)

# WebSocket endpoint for real-time grid data
@app.websocket("/grid-data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = get_simulation_state()
            await websocket.send_json(data)
            await asyncio.sleep(5)  # Update every 5 seconds
    except Exception as e:
        print(f"WebSocket closed: {e}")
        await websocket.close() 