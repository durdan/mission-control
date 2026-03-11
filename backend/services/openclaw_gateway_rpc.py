"""
OpenClaw Gateway WebSocket RPC Client
Direct WebSocket connection to OpenClaw gateway with full RPC protocol implementation
Protocol Version 3
"""

import asyncio
import json
import logging
import ssl
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4
from urllib.parse import urlparse

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)

# Protocol version
PROTOCOL_VERSION = 3

# Gateway events we can subscribe to
GATEWAY_EVENTS = [
    "connect.challenge",
    "agent",
    "chat",
    "presence",
    "tick",
    "talk.mode",
    "shutdown",
    "health",
    "heartbeat",
    "cron",
    "node.pair.requested",
    "node.pair.resolved",
    "node.invoke.request",
    "device.pair.requested",
    "device.pair.resolved",
    "approval.requested",
    "approval.resolved",
    "config.changed",
    "session.updated",
]

# Complete list of gateway methods (87 base + extensions)
GATEWAY_METHODS = [
    # Core system
    "health",
    "status",
    "wake",
    "system-presence",
    "system-event",
    
    # Logging
    "logs.tail",
    
    # Channels
    "channels.status",
    "channels.logout",
    
    # Usage and costs
    "usage.status",
    "usage.cost",
    
    # Text-to-Speech
    "tts.status",
    "tts.providers",
    "tts.enable",
    "tts.disable",
    "tts.convert",
    "tts.setProvider",
    
    # Configuration
    "config.get",
    "config.set",
    "config.apply",
    "config.patch",
    "config.schema",
    
    # Execution approvals
    "exec.approvals.get",
    "exec.approvals.set",
    "exec.approvals.node.get",
    "exec.approvals.node.set",
    "exec.approval.request",
    "exec.approval.resolve",
    
    # Wizard workflows
    "wizard.start",
    "wizard.next",
    "wizard.cancel",
    "wizard.status",
    
    # Talk mode
    "talk.mode",
    
    # Models
    "models.list",
    
    # Agents
    "agents.list",
    "agents.create",
    "agents.update",
    "agents.delete",
    "agents.files.list",
    "agents.files.get",
    "agents.files.set",
    
    # Skills
    "skills.status",
    "skills.bins",
    "skills.install",
    "skills.update",
    
    # Updates
    "update.run",
    
    # Voice wake
    "voicewake.get",
    "voicewake.set",
    
    # Sessions
    "sessions.list",
    "sessions.preview",
    "sessions.patch",
    "sessions.reset",
    "sessions.delete",
    "sessions.compact",
    
    # Heartbeats
    "last-heartbeat",
    "set-heartbeats",
    
    # Node pairing
    "node.pair.request",
    "node.pair.list",
    "node.pair.approve",
    "node.pair.reject",
    "node.pair.verify",
    
    # Device pairing
    "device.pair.list",
    "device.pair.approve",
    "device.pair.reject",
    "device.token.rotate",
    "device.token.revoke",
    
    # Node management
    "node.rename",
    "node.list",
    "node.describe",
    "node.invoke",
    "node.invoke.result",
    "node.event",
    
    # Cron jobs
    "cron.list",
    "cron.status",
    "cron.add",
    "cron.update",
    "cron.remove",
    "cron.run",
    "cron.runs",
    
    # Messaging
    "send",
    "agent",
    "agent.identity.get",
    "agent.wait",
    
    # Browser
    "browser.request",
    
    # Chat
    "chat.history",
    "chat.abort",
    "chat.send",
]


@dataclass
class RPCRequest:
    """RPC request message"""
    id: str
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
            "params": self.params
        }


@dataclass
class RPCResponse:
    """RPC response message"""
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RPCResponse':
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error")
        )


@dataclass
class RPCEvent:
    """RPC event notification"""
    method: str
    params: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RPCEvent':
        return cls(
            method=data.get("method", ""),
            params=data.get("params", {})
        )


class OpenClawGatewayRPC:
    """
    WebSocket RPC client for OpenClaw Gateway
    Implements Protocol Version 3
    """
    
    def __init__(
        self,
        gateway_url: str = "ws://127.0.0.1:18789",
        gateway_token: Optional[str] = None,
        client_id: str = "mission-control",
        client_mode: str = "operator"
    ):
        """
        Initialize the OpenClaw Gateway RPC client
        
        Args:
            gateway_url: WebSocket URL of the gateway
            gateway_token: Authentication token (if required)
            client_id: Client identifier
            client_mode: Client mode (operator, device, ui)
        """
        self.gateway_url = gateway_url
        self.gateway_token = gateway_token
        self.client_id = client_id
        self.client_mode = client_mode
        
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._receive_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Connect to the gateway"""
        try:
            # Parse URL
            parsed = urlparse(self.gateway_url)
            
            # Build connection headers
            headers = {
                "X-Client-Id": self.client_id,
                "X-Client-Mode": self.client_mode,
                "X-Protocol-Version": str(PROTOCOL_VERSION)
            }
            
            if self.gateway_token:
                headers["Authorization"] = f"Bearer {self.gateway_token}"
            
            # SSL context for wss://
            ssl_context = None
            if parsed.scheme == "wss":
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect (websockets 14.x API)
            additional_headers = list(headers.items()) if headers else None
            
            self._ws = await websockets.connect(
                self.gateway_url,
                additional_headers=additional_headers,
                ssl=ssl_context
            )
            
            self._connected = True
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Connected to OpenClaw Gateway at {self.gateway_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to gateway: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the gateway"""
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            
        if self._ws:
            await self._ws.close()
            self._ws = None
            
        logger.info("Disconnected from OpenClaw Gateway")
    
    async def _receive_loop(self):
        """Receive messages from the gateway"""
        try:
            async for message in self._ws:
                await self._handle_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            self._connected = False
    
    async def _handle_message(self, message: str):
        """Handle incoming message from gateway"""
        try:
            data = json.loads(message)
            
            # Check if it's a response to a request
            if "id" in data and data["id"] in self._pending_requests:
                response = RPCResponse.from_dict(data)
                future = self._pending_requests.pop(data["id"])
                
                if response.error:
                    future.set_exception(Exception(response.error))
                else:
                    future.set_result(response.result)
                    
            # Check if it's an event notification
            elif "method" in data and "id" not in data:
                event = RPCEvent.from_dict(data)
                await self._handle_event(event)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_event(self, event: RPCEvent):
        """Handle incoming event from gateway"""
        handlers = self._event_handlers.get(event.method, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.method}: {e}")
    
    def on_event(self, event_name: str, handler: Callable):
        """Register an event handler"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
    
    def off_event(self, event_name: str, handler: Callable):
        """Unregister an event handler"""
        if event_name in self._event_handlers:
            self._event_handlers[event_name].remove(handler)
    
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Any:
        """
        Call a gateway method
        
        Args:
            method: Method name
            params: Method parameters
            timeout: Request timeout in seconds
            
        Returns:
            Method result
            
        Raises:
            Exception: If method call fails
        """
        if not self._connected or not self._ws:
            raise Exception("Not connected to gateway")
        
        # Create request
        request = RPCRequest(
            id=str(uuid4()),
            method=method,
            params=params or {}
        )
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request.id] = future
        
        try:
            # Send request
            await self._ws.send(json.dumps(request.to_dict()))
            
            # Wait for response
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(request.id, None)
            raise Exception(f"Request timeout for method {method}")
        except Exception as e:
            self._pending_requests.pop(request.id, None)
            raise
    
    # Convenience methods for common operations
    
    async def health(self) -> Dict[str, Any]:
        """Get gateway health status"""
        return await self.call("health")
    
    async def status(self) -> Dict[str, Any]:
        """Get gateway status"""
        return await self.call("status")
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        return await self.call("sessions.list")
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        return await self.call("sessions.preview", {"sessionId": session_id})
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        return await self.call("sessions.delete", {"sessionId": session_id})
    
    async def reset_session(self, session_id: str) -> bool:
        """Reset a session"""
        return await self.call("sessions.reset", {"sessionId": session_id})
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        return await self.call("agents.list")
    
    async def create_agent(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent"""
        return await self.call("agents.create", {"name": name, "config": config})
    
    async def update_agent(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update an agent"""
        return await self.call("agents.update", {"agentId": agent_id, "config": config})
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        return await self.call("agents.delete", {"agentId": agent_id})
    
    async def send_chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message"""
        params = {"message": message}
        if session_id:
            params["sessionId"] = session_id
        return await self.call("chat.send", params)
    
    async def get_chat_history(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get chat history"""
        params = {"limit": limit}
        if session_id:
            params["sessionId"] = session_id
        return await self.call("chat.history", params)
    
    async def abort_chat(self, session_id: Optional[str] = None) -> bool:
        """Abort current chat"""
        params = {}
        if session_id:
            params["sessionId"] = session_id
        return await self.call("chat.abort", params)
    
    async def get_config(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration"""
        params = {}
        if path:
            params["path"] = path
        return await self.call("config.get", params)
    
    async def set_config(self, path: str, value: Any) -> bool:
        """Set configuration value"""
        return await self.call("config.set", {"path": path, "value": value})
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        return await self.call("models.list")
    
    async def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return await self.call("usage.status")
    
    async def get_cost(self) -> Dict[str, Any]:
        """Get cost information"""
        return await self.call("usage.cost")


# Singleton instance
_gateway_client: Optional[OpenClawGatewayRPC] = None


def get_gateway_client() -> OpenClawGatewayRPC:
    """Get the singleton gateway client instance"""
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = OpenClawGatewayRPC()
    return _gateway_client


async def initialize_gateway_client(
    gateway_url: str = "ws://127.0.0.1:18789",
    gateway_token: Optional[str] = None
) -> OpenClawGatewayRPC:
    """Initialize and connect the gateway client"""
    global _gateway_client
    _gateway_client = OpenClawGatewayRPC(
        gateway_url=gateway_url,
        gateway_token=gateway_token
    )
    await _gateway_client.connect()
    return _gateway_client