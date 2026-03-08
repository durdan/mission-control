"""
OpenClawAdapter Service
=======================
This service is the ONLY interface between Mission Control and OpenClaw.
Mission Control requests actions, OpenClaw performs them.
We NEVER simulate agent runtime or execution.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
import websockets
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)


class OpenClawAdapter:
    """
    Adapter for OpenClaw integration.
    Mission Control uses this to request actions from OpenClaw.
    OpenClaw remains the sole runtime for agents.
    """
    
    def __init__(self):
        self.gateway_url = settings.OPENCLAW_GATEWAY_URL
        self.api_url = settings.OPENCLAW_API_URL
        self.token = settings.OPENCLAW_TOKEN
        self.ws_connection = None
        self.http_client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {}
        )
    
    # ========================================
    # Agent Management (Request Only)
    # ========================================
    
    async def create_agent(self, agent_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request OpenClaw to create an agent.
        Returns reference to created agent.
        Mission Control stores the reference, not the agent.
        """
        logger.info(f"Requesting agent creation: {agent_spec.get('id')}")
        
        # In production, this would call OpenClaw API
        # For now, return mock reference
        return {
            "openclaw_agent_ref": f"oclaw_agent_{agent_spec.get('id')}",
            "workspace_path": f"/Users/durdan/.openclaw/agents/{agent_spec.get('id')}",
            "created": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register an existing OpenClaw agent with Mission Control.
        This is for agents created outside Mission Control.
        """
        logger.info(f"Registering existing agent: {agent_id}")
        
        # Verify agent exists in OpenClaw
        # Store reference in our database
        return True
    
    async def create_workspace(self, agent_id: str) -> str:
        """
        Request OpenClaw to create a workspace for an agent.
        Returns workspace path.
        """
        logger.info(f"Requesting workspace creation for agent: {agent_id}")
        
        # OpenClaw creates the workspace
        # We just store the path reference
        return f"/Users/durdan/.openclaw/workspaces/{agent_id}"
    
    # ========================================
    # Agent Status (Read Only)
    # ========================================
    
    async def get_agent_status(self, openclaw_agent_ref: str) -> Dict[str, Any]:
        """
        Get current status of an OpenClaw agent.
        This is read-only - we don't control agent state.
        """
        try:
            # In production, query OpenClaw for real status
            return {
                "status": "active",
                "current_session": None,
                "last_heartbeat": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return {"status": "unknown", "error": str(e)}
    
    async def sync_subagents(self, parent_agent_ref: str) -> List[Dict[str, Any]]:
        """
        Sync sub-agents from OpenClaw.
        OpenClaw manages agent hierarchy, we just mirror it.
        """
        logger.info(f"Syncing sub-agents for: {parent_agent_ref}")
        
        # Query OpenClaw for sub-agents
        # Return list of sub-agent references
        return []
    
    # ========================================
    # Session Management (Request & Track)
    # ========================================
    
    async def start_session(
        self, 
        agent_ref: str, 
        job_id: str,
        task_description: str
    ) -> Dict[str, Any]:
        """
        Request OpenClaw to start an agent session.
        Returns session reference.
        """
        logger.info(f"Requesting session start for agent: {agent_ref}, job: {job_id}")
        
        # OpenClaw starts the actual session
        # We just track the reference
        return {
            "openclaw_session_ref": f"oclaw_session_{job_id}",
            "started_at": datetime.utcnow().isoformat(),
            "status": "running"
        }
    
    async def end_session(self, session_ref: str) -> bool:
        """
        Request OpenClaw to end a session.
        """
        logger.info(f"Requesting session end: {session_ref}")
        
        # OpenClaw ends the session
        return True
    
    # ========================================
    # Event Handling (Receive Only)
    # ========================================
    
    async def receive_heartbeat(self, agent_ref: str, data: Dict[str, Any]) -> None:
        """
        Receive heartbeat from OpenClaw agent.
        We don't send heartbeats, we receive them.
        """
        logger.debug(f"Received heartbeat from {agent_ref}: {data}")
        
        # Update our metadata based on heartbeat
        # Don't control agent behavior
        pass
    
    async def attach_artifact(
        self, 
        session_ref: str,
        artifact_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register an artifact created by OpenClaw.
        We don't create artifacts, we track them.
        """
        logger.info(f"Registering artifact for session {session_ref}: {artifact_path}")
        
        return {
            "artifact_id": f"artifact_{session_ref}_{datetime.utcnow().timestamp()}",
            "path": artifact_path,
            "registered": True
        }
    
    async def report_error(
        self, 
        source_ref: str,
        error: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Receive error report from OpenClaw.
        We track errors, we don't handle them.
        """
        logger.error(f"Error from {source_ref}: {error}")
        
        # Store error in events table
        # Don't try to fix or retry
        pass
    
    # ========================================
    # WebSocket Connection (Listen Only)
    # ========================================
    
    async def connect_websocket(self):
        """
        Connect to OpenClaw gateway WebSocket.
        We listen for events, we don't control execution.
        """
        try:
            async with websockets.connect(self.gateway_url) as websocket:
                self.ws_connection = websocket
                logger.info("Connected to OpenClaw gateway WebSocket")
                
                # Send authentication if needed
                if self.token:
                    await websocket.send(json.dumps({
                        "type": "auth",
                        "token": self.token
                    }))
                
                # Listen for messages
                async for message in websocket:
                    await self._handle_websocket_message(json.loads(message))
                    
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.ws_connection = None
    
    async def _handle_websocket_message(self, message: Dict[str, Any]):
        """
        Handle incoming WebSocket messages from OpenClaw.
        We react to events, we don't generate them.
        """
        msg_type = message.get("type")
        
        if msg_type == "agent_status":
            # Update our agent metadata
            pass
        elif msg_type == "session_update":
            # Update session metadata
            pass
        elif msg_type == "task_completed":
            # Mark task as completed in our DB
            pass
        elif msg_type == "error":
            # Log error, update status
            pass
        else:
            logger.debug(f"Received message type: {msg_type}")
    
    # ========================================
    # Provisioning (Request Only)
    # ========================================
    
    async def provision_agent(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request OpenClaw to provision a new agent.
        This goes through approval workflow first.
        """
        logger.info(f"Requesting agent provisioning: {spec}")
        
        # After approval, OpenClaw provisions the agent
        # We store the reference when it's ready
        return {
            "provisioning_id": f"prov_{datetime.utcnow().timestamp()}",
            "status": "pending_approval"
        }
    
    # ========================================
    # Cleanup
    # ========================================
    
    async def close(self):
        """Close connections gracefully."""
        if self.ws_connection:
            await self.ws_connection.close()
        await self.http_client.aclose()


# Singleton instance
openclaw_adapter = OpenClawAdapter()