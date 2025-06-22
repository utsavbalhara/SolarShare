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

# Helper to get all trades from CSV
def get_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    df = pd.read_csv(TRADES_FILE)
    return df.to_dict(orient="records")

# Helper to get simulation state (dummy for now, can be replaced with real-time state)
def get_simulation_state():
    # For now, just return the latest trades as a proxy for grid activity
    trades = get_trades()
    return {"trades": trades}

# Metrics calculation endpoint
@app.get("/metrics")
def calculate_metrics():
    trades = get_trades()
    savings = sum(trade["kwh"] * 3.5 for trade in trades)  # ₹3.5/kWh baseline
    co2_reduced = sum(trade["kwh"] * 0.8 for trade in trades)  # 0.8 kg CO2 per kWh
    return {"savings": savings, "co2_reduced": co2_reduced}

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