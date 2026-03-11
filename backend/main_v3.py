#!/usr/bin/env python3
"""
Mission Control V3 API with WebSocket RPC
Direct connection to OpenClaw gateway via WebSocket RPC protocol
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
import logging
import os

# Import our WebSocket RPC client
from services import (
    OpenClawGatewayRPC,
    get_gateway_client,
    initialize_gateway_client,
    GATEWAY_METHODS,
    GATEWAY_EVENTS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mission Control V3 - WebSocket RPC",
    description="Direct OpenClaw Gateway integration via WebSocket RPC Protocol v3",
    version="3.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global gateway client
gateway_client: Optional[OpenClawGatewayRPC] = None

# Connected WebSocket clients for real-time updates
websocket_clients: List[WebSocket] = []


# Pydantic models
class SessionInfo(BaseModel):
    id: str
    name: str
    status: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    context_limit: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentInfo(BaseModel):
    id: str
    name: str
    status: str
    config: Dict[str, Any]


class GatewayStatus(BaseModel):
    connected: bool
    gateway_url: str
    protocol_version: int
    methods_available: int
    uptime: Optional[float] = None


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize gateway connection on startup"""
    global gateway_client
    
    # Get configuration from environment
    gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
    gateway_token = os.getenv("OPENCLAW_GATEWAY_TOKEN")
    
    try:
        # Initialize gateway client
        gateway_client = await initialize_gateway_client(
            gateway_url=gateway_url,
            gateway_token=gateway_token
        )
        
        # Register event handlers
        gateway_client.on_event("session.updated", handle_session_update)
        gateway_client.on_event("agent", handle_agent_event)
        gateway_client.on_event("chat", handle_chat_event)
        gateway_client.on_event("health", handle_health_event)
        
        logger.info(f"✅ Connected to OpenClaw Gateway at {gateway_url}")
        logger.info(f"📊 Protocol Version: {GATEWAY_METHODS}")
        logger.info(f"🔌 {len(GATEWAY_METHODS)} methods available")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to gateway: {e}")
        logger.warning("⚠️ Running in offline mode")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up gateway connection on shutdown"""
    global gateway_client
    
    if gateway_client:
        await gateway_client.disconnect()
        logger.info("Disconnected from OpenClaw Gateway")


# Event handlers
async def handle_session_update(event):
    """Handle session update events"""
    logger.info(f"Session update: {event.params}")
    await broadcast_to_websockets({
        "type": "session.update",
        "data": event.params
    })


async def handle_agent_event(event):
    """Handle agent events"""
    logger.info(f"Agent event: {event.params}")
    await broadcast_to_websockets({
        "type": "agent.event",
        "data": event.params
    })


async def handle_chat_event(event):
    """Handle chat events"""
    logger.info(f"Chat event: {event.params}")
    await broadcast_to_websockets({
        "type": "chat.event",
        "data": event.params
    })


async def handle_health_event(event):
    """Handle health events"""
    logger.info(f"Health event: {event.params}")
    await broadcast_to_websockets({
        "type": "health.event",
        "data": event.params
    })


async def broadcast_to_websockets(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    disconnected = []
    for client in websocket_clients:
        try:
            await client.send_json(message)
        except:
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        websocket_clients.remove(client)


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Mission Control V3",
        "description": "WebSocket RPC Gateway Integration",
        "protocol": "WebSocket RPC v3",
        "methods_available": len(GATEWAY_METHODS),
        "events_supported": len(GATEWAY_EVENTS),
        "docs": "http://localhost:8001/docs"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gateway_connected": gateway_client and gateway_client._connected
    }
    
    if gateway_client and gateway_client._connected:
        try:
            gateway_health = await gateway_client.health()
            health_status["gateway_health"] = gateway_health
        except:
            health_status["gateway_health"] = None
    
    return health_status


@app.get("/api/v3/gateway/status", response_model=GatewayStatus)
async def get_gateway_status() -> GatewayStatus:
    """Get gateway connection status"""
    if not gateway_client:
        raise HTTPException(status_code=503, detail="Gateway client not initialized")
    
    status = GatewayStatus(
        connected=gateway_client._connected,
        gateway_url=gateway_client.gateway_url,
        protocol_version=3,
        methods_available=len(GATEWAY_METHODS)
    )
    
    if gateway_client._connected:
        try:
            gateway_status = await gateway_client.status()
            status.uptime = gateway_status.get("uptime")
        except:
            pass
    
    return status


@app.get("/api/v3/gateway/methods")
async def list_gateway_methods() -> Dict[str, Any]:
    """List all available gateway methods"""
    return {
        "total": len(GATEWAY_METHODS),
        "methods": GATEWAY_METHODS,
        "categories": {
            "core": [m for m in GATEWAY_METHODS if m in ["health", "status", "wake"]],
            "sessions": [m for m in GATEWAY_METHODS if m.startswith("sessions.")],
            "agents": [m for m in GATEWAY_METHODS if m.startswith("agents.")],
            "chat": [m for m in GATEWAY_METHODS if m.startswith("chat.")],
            "config": [m for m in GATEWAY_METHODS if m.startswith("config.")],
            "skills": [m for m in GATEWAY_METHODS if m.startswith("skills.")],
            "node": [m for m in GATEWAY_METHODS if m.startswith("node.")],
            "device": [m for m in GATEWAY_METHODS if m.startswith("device.")],
            "cron": [m for m in GATEWAY_METHODS if m.startswith("cron.")],
            "other": [m for m in GATEWAY_METHODS if not any(
                m.startswith(p) for p in 
                ["sessions.", "agents.", "chat.", "config.", "skills.", "node.", "device.", "cron."]
            ) and m not in ["health", "status", "wake"]]
        }
    }


@app.post("/api/v3/gateway/call")
async def call_gateway_method(method: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Call any gateway method directly"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    if method not in GATEWAY_METHODS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
    
    try:
        result = await gateway_client.call(method, params)
        return {"method": method, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Sessions API
@app.get("/api/v3/sessions", response_model=List[SessionInfo])
async def list_sessions(demo: bool = Query(False)) -> List[SessionInfo]:
    """List all OpenClaw sessions"""
    if demo or not gateway_client or not gateway_client._connected:
        # Return demo data
        return [
            SessionInfo(
                id="demo-session-1",
                name="Demo Session 1",
                status="active",
                model="claude-3-sonnet",
                tokens_used=1234,
                context_limit=200000,
                created_at=datetime.now().isoformat()
            )
        ]
    
    try:
        sessions_data = await gateway_client.list_sessions()
        sessions = []
        
        for session in sessions_data:
            sessions.append(SessionInfo(
                id=session.get("id", ""),
                name=session.get("name", ""),
                status=session.get("status", "unknown"),
                model=session.get("model"),
                tokens_used=session.get("tokens_used"),
                context_limit=session.get("context_limit"),
                created_at=session.get("created_at"),
                updated_at=session.get("updated_at")
            ))
        
        return sessions
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get specific session details"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        session = await gateway_client.get_session(session_id)
        return SessionInfo(
            id=session.get("id", session_id),
            name=session.get("name", ""),
            status=session.get("status", "unknown"),
            model=session.get("model"),
            tokens_used=session.get("tokens_used"),
            context_limit=session.get("context_limit"),
            created_at=session.get("created_at"),
            updated_at=session.get("updated_at")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v3/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        await gateway_client.delete_session(session_id)
        return {"message": f"Session {session_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/sessions/{session_id}/reset")
async def reset_session(session_id: str) -> Dict[str, str]:
    """Reset a session"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        await gateway_client.reset_session(session_id)
        return {"message": f"Session {session_id} reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Agents API
@app.get("/api/v3/agents", response_model=List[AgentInfo])
async def list_agents(demo: bool = Query(False)) -> List[AgentInfo]:
    """List all agents"""
    if demo or not gateway_client or not gateway_client._connected:
        # Return demo data
        return [
            AgentInfo(
                id="demo-agent-1",
                name="Demo Agent",
                status="active",
                config={"model": "claude-3-sonnet"}
            )
        ]
    
    try:
        agents_data = await gateway_client.list_agents()
        agents = []
        
        for agent in agents_data:
            agents.append(AgentInfo(
                id=agent.get("id", ""),
                name=agent.get("name", ""),
                status=agent.get("status", "unknown"),
                config=agent.get("config", {})
            ))
        
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/agents")
async def create_agent(name: str, config: Dict[str, Any]) -> AgentInfo:
    """Create a new agent"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        agent = await gateway_client.create_agent(name, config)
        return AgentInfo(
            id=agent.get("id", ""),
            name=agent.get("name", name),
            status=agent.get("status", "created"),
            config=agent.get("config", config)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v3/agents/{agent_id}")
async def delete_agent(agent_id: str) -> Dict[str, str]:
    """Delete an agent"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        await gateway_client.delete_agent(agent_id)
        return {"message": f"Agent {agent_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Chat API
@app.post("/api/v3/chat/send")
async def send_chat(message: ChatMessage) -> Dict[str, Any]:
    """Send a chat message"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        result = await gateway_client.send_chat(message.message, message.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/chat/history")
async def get_chat_history(session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get chat history"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        history = await gateway_client.get_chat_history(session_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/chat/abort")
async def abort_chat(session_id: Optional[str] = None) -> Dict[str, str]:
    """Abort current chat"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        await gateway_client.abort_chat(session_id)
        return {"message": "Chat aborted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Configuration API
@app.get("/api/v3/config")
async def get_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Get configuration"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        config = await gateway_client.get_config(path)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v3/config")
async def set_config(path: str, value: Any) -> Dict[str, str]:
    """Set configuration value"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        await gateway_client.set_config(path, value)
        return {"message": f"Config {path} updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Models API
@app.get("/api/v3/models")
async def list_models() -> List[Dict[str, Any]]:
    """List available models"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        models = await gateway_client.list_models()
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Usage API
@app.get("/api/v3/usage")
async def get_usage() -> Dict[str, Any]:
    """Get usage statistics"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        usage = await gateway_client.get_usage()
        return usage
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/usage/cost")
async def get_cost() -> Dict[str, Any]:
    """Get cost information"""
    if not gateway_client or not gateway_client._connected:
        raise HTTPException(status_code=503, detail="Gateway not connected")
    
    try:
        cost = await gateway_client.get_cost()
        return cost
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            # Wait for messages from client (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back as pong
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        websocket_clients.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


# Server-Sent Events endpoint for streaming updates
@app.get("/api/v3/events")
async def stream_events():
    """Server-Sent Events endpoint for streaming updates"""
    async def event_generator():
        """Generate SSE events"""
        while True:
            if gateway_client and gateway_client._connected:
                try:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                except:
                    pass
            
            await asyncio.sleep(5)  # Send heartbeat every 5 seconds
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Mission Control V3 with WebSocket RPC...")
    print("📡 Connecting to OpenClaw Gateway via WebSocket...")
    print(f"🔌 {len(GATEWAY_METHODS)} gateway methods available")
    print(f"📊 {len(GATEWAY_EVENTS)} event types supported")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("🌐 WebSocket: ws://localhost:8001/ws")
    print("📡 SSE Stream: http://localhost:8001/api/v3/events")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)