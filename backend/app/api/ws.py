# WebSocket API router for real-time sensor data streaming with connection management, client subscriptions, and live dashboard updates via the global connection manager.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Any, List
import json
import asyncio
import logging
from datetime import datetime

from app.core.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Use a dependency to get the connection manager
def get_connection_manager():
    # In a real app, this could be a more complex dependency,
    # but for now, it returns a global instance.
    return ConnectionManager()

@router.websocket("/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_connection_manager)
):
    """WebSocket endpoint for dashboard real-time updates."""
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to IDES 2.0 real-time updates",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                message = json.loads(data)
                await handle_client_message(websocket, message, manager)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket)

async def handle_client_message(websocket: WebSocket, message: Dict[str, Any], manager: ConnectionManager):
    """Handle incoming messages from WebSocket clients."""
    message_type = message.get("type")
    
    response = {"type": "response", "request_type": message_type}
    
    if message_type == "pong":
        # Client is responding to our ping, no action needed
        return
        
    elif message_type == "subscribe":
        streams = message.get("streams", [])
        # Here you could store subscription state in the manager
        response.update({"status": "success", "subscribed_to": streams})
        
    elif message_type == "request_data":
        metric = message.get("metric")
        # In a real implementation, fetch data asynchronously
        response.update({"metric": metric, "data": []}) # Placeholder
        
    else:
        response.update({"status": "error", "message": f"Unknown message type: {message_type}"})

    await websocket.send_json(response)

@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time alert notifications."""
    await websocket.accept()
    
    try:
        await websocket.send_json({
            "type": "alerts_connected",
            "message": "Connected to IDES 2.0 alert system",
            "available_alerts": ["temperature_threshold", "humidity_threshold", "co2_threshold"]
        })
        
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "configure_alert":
                await websocket.send_json({
                    "type": "alert_configured",
                    "alert_id": message.get("alert_id"),
                })
                
    except WebSocketDisconnect:
        logger.info("Alerts WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"Alerts WebSocket error: {e}", exc_info=True)

# These functions can be called from other parts of the application
# to push data to clients.
async def broadcast_sensor_update(manager: ConnectionManager, data: Dict[str, Any]):
    """Broadcast sensor data update to all connected dashboard clients."""
    await manager.broadcast_sensor_update(data)

async def broadcast_alert(manager: ConnectionManager, alert_data: Dict[str, Any]):
    """Broadcast alert to all connected clients."""
    message = {
        "type": "alert",
        "timestamp": datetime.utcnow().isoformat(),
        "data": alert_data
    }
    await manager.broadcast(message)

async def broadcast_forecast_update(manager: ConnectionManager, forecast_data: Dict[str, Any]):
    """Broadcast forecast update to all connected clients."""
    await manager.broadcast_forecast_update(forecast_data)

def get_connection_stats(manager: ConnectionManager) -> Dict[str, Any]:
    """Get WebSocket connection statistics."""
    return {"active_connections": manager.get_connection_count()}