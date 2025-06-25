#!/usr/bin/env python3
"""
SolarShare Production Entry Point
Combines simulation engine, backend API, and frontend serving for deployment
"""

import asyncio
import threading
import os
import time
import subprocess
import sys
from fastapi.staticfiles import StaticFiles

# Import the existing backend app
from backend import app as backend_app

def start_simulation():
    """Start simulation engine in background thread"""
    print("⚡ Starting SolarShare Simulation Engine...")
    try:
        # Give a moment for the main app to initialize
        time.sleep(2)
        subprocess.Popen([sys.executable, "simulation_engine.py"])
    except Exception as e:
        print(f"Error starting simulation engine: {e}")

def setup_app():
    """Setup the combined FastAPI app with static file serving"""
    # Mount static files to serve the frontend
    backend_app.mount("/", StaticFiles(directory=".", html=True), name="static")
    return backend_app

if __name__ == "__main__":
    print("🌞 Starting SolarShare for Production Deployment")
    
    # Setup the combined app
    app = setup_app()
    
    # Start simulation engine in background thread
    simulation_thread = threading.Thread(target=start_simulation, daemon=True)
    simulation_thread.start()
    
    # Get port from environment (DigitalOcean sets this)
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting SolarShare on port {port}")
    
    # Start the server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)