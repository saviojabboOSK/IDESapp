# WebSocket API router for real-time sensor data streaming with connection management, client subscriptions, and live dashboard updates via the global connection manager.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json
import asyncio
import logging

from app.core.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Global connection manager instance (shared with main.py)
manager = ConnectionManager()

@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            json.dumps({
                "type": "connection_established",
                "message": "Connected to IDES 2.0 real-time updates",
                "timestamp": asyncio.get_event_loop().time()
            }),
            websocket
        )
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Receive message from client with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": "Invalid JSON format"
                        }),
                        websocket
                    )
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_personal_message(
                    json.dumps({"type": "ping", "timestamp": asyncio.get_event_loop().time()}),
                    websocket
                )
                
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming messages from WebSocket clients."""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(
            json.dumps({
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time()
            }),
            websocket
        )
        
    elif message_type == "subscribe":
        # Handle subscription to specific data streams
        streams = message.get("streams", [])
        await manager.send_personal_message(
            json.dumps({
                "type": "subscription_confirmed",
                "streams": streams,
                "message": f"Subscribed to {len(streams)} data streams"
            }),
            websocket
        )
        
    elif message_type == "request_data":
        # Handle request for specific data
        metric = message.get("metric")
        timeframe = message.get("timeframe", "1h")
        
        # This would fetch and send requested data
        await manager.send_personal_message(
            json.dumps({
                "type": "data_response",
                "metric": metric,
                "timeframe": timeframe,
                "data": [],  # Would contain actual data
                "message": f"Data for {metric} over {timeframe}"
            }),
            websocket
        )
        
    else:
        # Unknown message type
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }),
            websocket
        )

@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time alert notifications."""
    await websocket.accept()
    
    try:
        # Send initial alerts configuration
        await websocket.send_text(json.dumps({
            "type": "alerts_connected",
            "message": "Connected to IDES 2.0 alert system",
            "available_alerts": [
                "temperature_threshold",
                "humidity_threshold", 
                "co2_threshold",
                "aqi_threshold",
                "sensor_offline"
            ]
        }))
        
        # Keep connection alive for alerts
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "configure_alert":
                # Handle alert configuration
                await websocket.send_text(json.dumps({
                    "type": "alert_configured",
                    "alert_id": message.get("alert_id"),
                    "message": "Alert configuration updated"
                }))
                
    except WebSocketDisconnect:
        logger.info("Alerts WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Alerts WebSocket error: {e}")

# Utility functions for broadcasting to WebSocket clients
async def broadcast_sensor_update(data: Dict[str, Any]):
    """Broadcast sensor data update to all connected dashboard clients."""
    await manager.broadcast_sensor_update(data)

async def broadcast_alert(alert_data: Dict[str, Any]):
    """Broadcast alert to all connected clients."""
    message = {
        "type": "alert",
        "timestamp": asyncio.get_event_loop().time(),
        "data": alert_data
    }
    await manager.broadcast(message)

async def broadcast_forecast_update(forecast_data: Dict[str, Any]):
    """Broadcast forecast update to all connected clients."""
    await manager.broadcast_forecast_update(forecast_data)

def get_connection_stats():
    """Get WebSocket connection statistics."""
    return {
        "active_connections": manager.get_connection_count(),
        "connection_details": [
            {
                "client_id": info.get("client_id"),
                "connected_at": info.get("connected_at"),
                "duration": asyncio.get_event_loop().time() - info.get("connected_at", 0)
            }
            for info in manager.connection_info.values()
        ]
    }