import asyncio
import pandas as pd
from fastapi import FastAPI, WebSocket, Path, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
from datetime import datetime, timedelta
from typing import Optional
import statistics

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
CONTROLS_FILE = "simulation_controls.json"
PARAMS_FILE = "simulation_params.json"

# Global variables for metrics calculation
previous_metrics = None
metrics_history = []

# Helper to get all trades from CSV
def get_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    df = pd.read_csv(TRADES_FILE)
    return df.to_dict(orient="records")

def get_controls():
    """Reads control states from a JSON file."""
    if not os.path.exists(CONTROLS_FILE):
        # Create the file with default values if it doesn't exist
        with open(CONTROLS_FILE, "w") as f:
            default_controls = {"fast_forward_nights": False, "slow_down_days": False}
            json.dump(default_controls, f)
        return default_controls
    
    try:
        with open(CONTROLS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"fast_forward_nights": False, "slow_down_days": False}

def write_controls(controls_data: dict):
    """Writes control states to a JSON file."""
    with open(CONTROLS_FILE, "w") as f:
        json.dump(controls_data, f)

def get_simulation_params():
    """Reads simulation parameters from JSON file."""
    if not os.path.exists(PARAMS_FILE):
        return None
    
    try:
        with open(PARAMS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def write_simulation_params(params_data: dict):
    """Writes simulation parameters to JSON file."""
    with open(PARAMS_FILE, "w") as f:
        json.dump(params_data, f)

def get_household_state():
    if not os.path.exists(HOUSEHOLD_STATE_FILE):
        return {"households": {}, "hour": None}
    with open(HOUSEHOLD_STATE_FILE, "r") as f:
        data = json.load(f)
        if isinstance(data, list) and data:
            return data[-1]  # Return latest entry
        return data

def get_all_household_states():
    """Get all historical household states"""
    if not os.path.exists(HOUSEHOLD_STATE_FILE):
        return []
    with open(HOUSEHOLD_STATE_FILE, "r") as f:
        data = json.load(f)
        return data if isinstance(data, list) else [data]

def calculate_resilience_score(households):
    """Calculate community resilience score (0-100)"""
    if not households:
        return 50
    
    total_battery = sum(h.get('battery', 0) for h in households)
    avg_battery = total_battery / len(households)
    
    active_trades = sum(1 for h in households if h.get('role') in ['seller', 'buyer'])
    trade_ratio = active_trades / len(households) if households else 0
    
    # Simple resilience calculation based on battery levels and trading activity
    resilience = (avg_battery * 0.6) + (trade_ratio * 40)
    return min(100, max(0, int(resilience)))

def calculate_metrics_deltas(current_metrics, previous_metrics):
    """Calculate change deltas for metrics"""
    if not previous_metrics:
        return {"delta_energy": "+0.0", "delta_savings": "+0.0", "delta_co2": "+0.0", "delta_resilience": "+0"}
    
    deltas = {}
    delta_keys = {
        'energy_traded': 'delta_energy',
        'cost_savings': 'delta_savings', 
        'co2_reduced': 'delta_co2',
        'resilience': 'delta_resilience'
    }
    
    for key, delta_key in delta_keys.items():
        current = current_metrics.get(key, 0)
        previous = previous_metrics.get(key, 0)
        delta = current - previous
        prefix = "+" if delta >= 0 else ""
        if key == 'resilience':
            deltas[delta_key] = f"{prefix}{int(delta)}"
        else:
            deltas[delta_key] = f"{prefix}{delta:.1f}"
    
    return deltas

# Helper to get simulation state (now includes household state and trades)
def get_simulation_state():
    trades = get_trades()
    household_state = get_household_state()
    return {"trades": trades, "household_state": household_state}

# Enhanced metrics calculation endpoint
@app.get("/metrics")
def get_latest_metrics():
    """Returns the latest metrics from the simulation with deltas"""
    global previous_metrics, metrics_history
    
    if not os.path.exists(HOUSEHOLD_STATE_FILE):
        return JSONResponse(content={"error": "Simulation data not found."}, status_code=404)
    
    try:
        household_state = get_household_state()
        trades = get_trades()
        
        if not household_state or 'households' not in household_state:
            return JSONResponse(content={"error": "No simulation data available yet."}, status_code=404)
        
        households = household_state.get('households', [])
        
        # Calculate current metrics
        total_energy_traded = sum(float(trade.get('kwh', 0)) for trade in trades)
        total_cost_savings = sum(float(trade.get('kwh', 0)) * float(trade.get('price', 0.15)) for trade in trades)
        co2_reduction = total_energy_traded * 0.5  # 0.5 kg CO2 per kWh
        resilience = calculate_resilience_score(households)
        
        current_metrics = {
            "energy_traded": round(total_energy_traded, 1),
            "cost_savings": round(total_cost_savings, 1),
            "co2_reduced": round(co2_reduction, 1),
            "resilience": resilience
        }
        
        # Calculate deltas
        deltas = calculate_metrics_deltas(current_metrics, previous_metrics)
        
        # Update previous metrics
        previous_metrics = current_metrics.copy()
        
        # Store in history
        metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            **current_metrics
        })
        
        # Keep only last 1000 entries
        if len(metrics_history) > 1000:
            metrics_history = metrics_history[-1000:]
        
        return JSONResponse(content={**current_metrics, **deltas})
        
    except Exception as e:
        return JSONResponse(content={"error": f"Error calculating metrics: {str(e)}"}, status_code=500)

# WebSocket endpoint for real-time state updates
@app.websocket("/state")
async def state_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            household_state = get_household_state()
            
            if household_state and 'households' in household_state:
                # Get weather data - with fallback defaults
                weather_data = household_state.get("weather", {
                    "temp": 22.5,
                    "clouds": 30,
                    "solar_radiation": 800,
                    "humidity": 65
                })
                
                # Get recent trades from CSV file
                all_trades = get_trades()
                # Get only recent trades (last 10) to avoid sending too much data
                recent_trades = all_trades[-10:] if all_trades else []
                
                # Get control states
                controls = get_controls()
                
                # Format data for frontend
                state_data = {
                    "timestamp": household_state.get("timestamp", datetime.now().isoformat()),
                    "households": household_state.get("households", []),
                    "trades": recent_trades,
                    "weather": weather_data,
                    "controls": controls
                }
                
                # Log once every 30 seconds (15 WebSocket calls) to verify data flow
                if hasattr(state_websocket, '_call_count'):
                    state_websocket._call_count += 1
                else:
                    state_websocket._call_count = 1
                    
                if state_websocket._call_count % 15 == 0:
                    print(f"Backend: Sending timestamp: {state_data['timestamp']}")
                    print(f"Backend: Weather temp: {weather_data.get('temp', 'N/A')}°C")
                
                await websocket.send_json(state_data)
            await asyncio.sleep(1)  # Update every 1 second to match simulation frequency
    except Exception as e:
        print(f"State WebSocket closed: {e}")
        await websocket.close()

# WebSocket endpoint for real-time grid data (legacy)
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

# Simulation Control Endpoints
@app.get("/controls/status")
def get_controls_status():
    """Returns the current state of simulation controls."""
    return JSONResponse(content=get_controls())

@app.post("/controls/fast-forward-nights")
def toggle_fast_forward_nights():
    """Toggles the fast-forward nights setting."""
    controls = get_controls()
    controls["fast_forward_nights"] = not controls.get("fast_forward_nights", False)
    write_controls(controls)
    return JSONResponse(content=controls)

@app.post("/controls/slow-down-days")
def toggle_slow_down_days():
    """Toggles the slow-down days setting."""
    controls = get_controls()
    controls["slow_down_days"] = not controls.get("slow_down_days", False)
    write_controls(controls)
    return JSONResponse(content=controls)

# Simulation Parameters Endpoints
@app.get("/simulation/config")
def get_simulation_config():
    """Returns the current simulation parameters configuration."""
    params = get_simulation_params()
    return JSONResponse(content={
        "custom_enabled": params is not None,
        "parameters": params if params else {}
    })

@app.post("/simulation/config")
async def set_simulation_config(request: Request):
    """Sets simulation parameters configuration."""
    try:
        body = await request.json()
        # Validate and set parameters
        if body.get("enabled", False):
            params = body.get("parameters", {})
            # Add validation here if needed
            write_simulation_params(params)
        else:
            # Remove custom parameters file to revert to defaults
            if os.path.exists(PARAMS_FILE):
                os.remove(PARAMS_FILE)
        
        return JSONResponse(content={"success": True, "message": "Configuration updated"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

@app.delete("/simulation/config")
def reset_simulation_config():
    """Resets simulation parameters to defaults."""
    try:
        if os.path.exists(PARAMS_FILE):
            os.remove(PARAMS_FILE)
        return JSONResponse(content={"success": True, "message": "Configuration reset to defaults"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

# History endpoint for time-series data
@app.get("/history")
def get_history(
    range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    metric: str = Query("energy_traded", description="Metric to return")
):
    """Returns historical time-series data for charts"""
    try:
        # Use metrics history if available, otherwise generate from household states
        if metrics_history:
            data = metrics_history
        else:
            # Fallback to household states
            states = get_all_household_states()
            data = []
            for state in states:
                if 'timestamp' in state:
                    households = state.get('households', [])
                    total_energy = sum(h.get('solar', 0) - h.get('demand', 0) for h in households)
                    data.append({
                        "timestamp": state['timestamp'],
                        "energy_traded": max(0, total_energy),
                        "cost_savings": max(0, total_energy) * 0.15,
                        "co2_reduced": max(0, total_energy) * 0.5,
                        "resilience": calculate_resilience_score(households)
                    })
        
        # Filter by time range
        now = datetime.now()
        if range == "1h":
            cutoff = now - timedelta(hours=1)
        elif range == "24h":
            cutoff = now - timedelta(hours=24)
        elif range == "7d":
            cutoff = now - timedelta(days=7)
        elif range == "30d":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = now - timedelta(hours=24)
        
        filtered_data = []
        for entry in data:
            try:
                entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if entry_time >= cutoff:
                    filtered_data.append(entry)
            except:
                continue
        
        return JSONResponse(content={
            "range": range,
            "data": filtered_data[-100:]  # Limit to last 100 points
        })
        
    except Exception as e:
        return JSONResponse(content={"error": f"Error fetching history: {str(e)}"}, status_code=500)

# Household details endpoint
@app.get("/households/{household_id}/details")
def get_household_details(household_id: str = Path(..., description="Household ID")):
    """Returns detailed information about a specific household"""
    try:
        household_state = get_household_state()
        trades = get_trades()
        
        if not household_state or 'households' not in household_state:
            return JSONResponse(content={"error": "No household data available"}, status_code=404)
        
        # Find the household
        household = None
        for h in household_state['households']:
            if h.get('id') == household_id:
                household = h
                break
        
        if not household:
            return JSONResponse(content={"error": "Household not found"}, status_code=404)
        
        # Get recent trades for this household
        recent_trades = []
        for trade in trades[-20:]:  # Last 20 trades
            if trade.get('seller') == household_id or trade.get('buyer') == household_id:
                trade_type = "sell" if trade.get('seller') == household_id else "buy"
                partner = trade.get('buyer') if trade_type == "sell" else trade.get('seller')
                recent_trades.append({
                    "timestamp": trade.get('timestamp', ''),
                    "type": trade_type,
                    "partner": partner,
                    "kwh": float(trade.get('kwh', 0)),
                    "price": float(trade.get('price', 0))
                })
        
        # Calculate performance metrics
        battery_level = household.get('battery', 0)
        efficiency = min(100, max(0, battery_level + (len(recent_trades) * 5)))
        trading_score = min(100, len(recent_trades) * 10)
        
        contribution = "high" if trading_score > 70 else "medium" if trading_score > 30 else "low"
        
        return JSONResponse(content={
            "household": {
                "id": household_id,
                "solar_capacity": household.get('solar_capacity', 4.5),
                "battery_size": household.get('battery_size', 12.0),
                "orientation": household.get('orientation', 'south'),
                "type": household.get('type', 'standard'),
                "current_battery": household.get('battery', 0),
                "current_role": household.get('role', 'idle'),
                "solar_generation": household.get('solar', 0),
                "demand": household.get('demand', 0)
            },
            "recent_trades": recent_trades,
            "performance": {
                "efficiency": efficiency,
                "trading_score": trading_score,
                "community_contribution": contribution
            }
        })
        
    except Exception as e:
        return JSONResponse(content={"error": f"Error fetching household details: {str(e)}"}, status_code=500)

# Mount static files to serve frontend - MUST be last
app.mount("/", StaticFiles(directory=".", html=True), name="static") 