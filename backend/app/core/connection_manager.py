# WebSocket connection manager for real-time sensor data broadcasting to multiple dashboard clients with automatic connection handling and message distribution.

from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time data updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "connected_at": asyncio.get_event_loop().time(),
            "client_id": len(self.active_connections)
        }
        logger.info(f"New WebSocket connection established. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            logger.info(f"WebSocket connection closed. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast sensor data update to all connected clients."""
        if not self.active_connections:
            return
        
        json_message = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                disconnected.append(connection)
        
        # Clean up failed connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_sensor_update(self, sensor_data: Dict[str, Any]):
        """Broadcast new sensor readings to all dashboard clients."""
        message = {
            "type": "sensor_update",
            "timestamp": sensor_data.get("timestamp"),
            "data": sensor_data,
            "source": "influx_worker"
        }
        await self.broadcast(message)
    
    async def broadcast_forecast_update(self, forecast_data: Dict[str, Any]):
        """Broadcast forecast data to all connected clients."""
        message = {
            "type": "forecast_update",
            "data": forecast_data,
            "source": "forecast_worker"
        }
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get number of active WebSocket connections."""
        return len(self.active_connections)