# FastAPI application entry point that orchestrates the Indoor Digital Environment System with real-time sensor data streaming, AI-powered chart generation, and WebSocket connections for live dashboard updates.

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from typing import Dict, Any

from app.core.config import settings
from app.core.connection_manager import ConnectionManager
from app.core.scheduler import start_scheduler
from app.api.graphs import router as graphs_router
from app.api.prompt import router as prompt_router
from app.api.settings import router as settings_router
from app.api.ws import router as ws_router

# Global connection manager for WebSocket clients
manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    print("🚀 Starting IDES 2.0 - Indoor Digital Environment System")
    await start_scheduler()
    print("📊 Background workers started for sensor data collection")
    
    # Trigger initial data collection to ensure graphs have data immediately
    from app.workers.influx import InfluxWorker
    influx_worker = InfluxWorker()
    try:
        print("🔄 Running initial sensor data collection...")
        await influx_worker.collect_sensor_data()
        print("✅ Initial data collection completed")
    except Exception as e:
        print(f"⚠️ Initial data collection failed: {e}")
    
    yield
    # Shutdown
    print("🛑 Shutting down IDES 2.0")

app = FastAPI(
    title="IDES 2.0 API",
    description="Indoor Digital Environment System - Real-time sensor data visualization with AI insights",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(graphs_router, prefix="/api/graphs", tags=["graphs"])
app.include_router(prompt_router, prefix="/api/prompt", tags=["prompt"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])

@app.get("/")
async def root():
    """Health check endpoint returning system status."""
    return {
        "message": "IDES 2.0 - Indoor Digital Environment System",
        "status": "online",
        "version": "2.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check for monitoring services."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "websocket": "connected" if manager.active_connections else "no_clients",
            "scheduler": "active"
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time sensor data updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)