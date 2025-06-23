#!/usr/bin/env python3
"""
SolarShare Dashboard Startup Script
Starts both the backend API and frontend web server
"""

import subprocess
import threading
import time
import os
import signal
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP Server that handles requests in separate threads"""
    pass

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler with CORS support"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

def start_simulation():
    """Start the simulation engine"""
    print("⚡ Starting SolarShare Simulation Engine...")
    cmd = [sys.executable, "simulation_engine.py"]
    return subprocess.Popen(cmd, cwd=os.getcwd())

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting SolarShare Backend API...")
    cmd = [
        sys.executable, "-m", "uvicorn", "backend:app",
        "--reload", "--host", "0.0.0.0", "--port", "8000"
    ]
    return subprocess.Popen(cmd, cwd=os.getcwd())

def start_frontend():
    """Start the frontend web server"""
    print("🌐 Starting SolarShare Frontend Server...")
    server = ThreadingHTTPServer(('localhost', 3000), CORSRequestHandler)
    server.serve_forever()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutting down SolarShare Dashboard...")
    sys.exit(0)

def main():
    print("=" * 60)
    print("🌞 SolarShare Community Energy Trading Dashboard")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start simulation engine in a separate process
    simulation_process = start_simulation()
    
    # Give simulation time to start
    time.sleep(2)
    
    # Start backend in a separate process
    backend_process = start_backend()
    
    # Give backend time to start
    time.sleep(3)
    
    # Start frontend server in a separate thread
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()
    
    # Give frontend time to start
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ SolarShare Dashboard is now running!")
    print("=" * 60)
    print(f"📊 Frontend Dashboard: http://localhost:3000")
    print(f"🔌 Backend API:       http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    print("💡 Features Available:")
    print("   • Real-time energy flow visualization")
    print("   • Household battery and role monitoring")
    print("   • Impact metrics with trend analysis")
    print("   • Weather conditions display")
    print("   • Interactive household details")
    print("   • Live activity feed")
    print("=" * 60)
    print("🚨 Press Ctrl+C to stop the dashboard")
    print("=" * 60)
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        simulation_process.terminate()
        backend_process.terminate()
        simulation_process.wait()
        backend_process.wait()
        print("✅ Dashboard stopped successfully!")

if __name__ == "__main__":
    main()