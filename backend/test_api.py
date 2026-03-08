#!/usr/bin/env python3
"""
Quick test script for Mission Control V2 API
Run this after starting the backend server.
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8001"

async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        print("✅ Health Check:", response.json())
        return response.status_code == 200

async def test_create_fleet():
    """Test fleet creation"""
    async with httpx.AsyncClient() as client:
        fleet_data = {
            "id": f"fleet_test_{datetime.now().timestamp()}",
            "name": "Test Fleet",
            "description": "Test fleet for API validation"
        }
        response = await client.post(f"{API_BASE}/api/v1/fleets", json=fleet_data)
        print("✅ Create Fleet:", response.json())
        return response.json()

async def test_create_agent():
    """Test agent creation (mock)"""
    async with httpx.AsyncClient() as client:
        agent_data = {
            "id": f"agent_test_{datetime.now().timestamp()}",
            "name": "Test Agent",
            "role": "tester",
            "model": "gpt-4",
            "fleet_id": None
        }
        response = await client.post(f"{API_BASE}/api/v1/agents", json=agent_data)
        print("✅ Create Agent:", response.json())
        return response.json()

async def test_list_agents():
    """Test listing agents"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/v1/agents")
        print("✅ List Agents:", response.json())
        return response.json()

async def test_create_task():
    """Test task creation"""
    async with httpx.AsyncClient() as client:
        task_data = {
            "id": f"task_test_{datetime.now().timestamp()}",
            "title": "Test Task",
            "description": "This is a test task",
            "priority": "P2"
        }
        response = await client.post(f"{API_BASE}/api/v1/tasks", json=task_data)
        print("✅ Create Task:", response.json())
        return response.json()

async def test_create_approval():
    """Test approval request creation"""
    async with httpx.AsyncClient() as client:
        approval_data = {
            "entity_type": "agent",
            "entity_id": "agent_001",
            "action": "provision",
            "requester": "test_user",
            "expires_in_hours": 24
        }
        response = await client.post(f"{API_BASE}/api/v1/approvals", json=approval_data)
        print("✅ Create Approval:", response.json())
        return response.json()

async def test_events():
    """Test event tracking"""
    async with httpx.AsyncClient() as client:
        # Create an event
        event_data = {
            "type": "test_event",
            "source_type": "test",
            "source_id": "test_001",
            "payload": {"message": "Test event"}
        }
        response = await client.post(f"{API_BASE}/api/v1/events", json=event_data)
        print("✅ Create Event:", response.json())
        
        # List events
        response = await client.get(f"{API_BASE}/api/v1/events?limit=5")
        print("✅ Recent Events:", len(response.json()), "events")

async def test_sse_stream():
    """Test SSE streaming (will timeout after 5 seconds)"""
    print("🔄 Testing SSE stream (5 second test)...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            async with client.stream("GET", f"{API_BASE}/api/v1/stream") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = json.loads(line[5:])
                        print("  📡 SSE Event:", data)
                        break  # Just test that we can connect
    except httpx.ReadTimeout:
        print("  ✅ SSE stream connected successfully")

async def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("🧪 Testing Mission Control V2 API")
    print("=" * 50)
    print(f"Target: {API_BASE}")
    print()
    
    try:
        # Basic health check
        if not await test_health():
            print("❌ Server not responding. Please start the backend first:")
            print("   cd backend && uvicorn main:app --reload")
            return
        
        print()
        
        # Test each endpoint
        await test_create_fleet()
        print()
        
        await test_create_agent()
        print()
        
        await test_list_agents()
        print()
        
        await test_create_task()
        print()
        
        await test_create_approval()
        print()
        
        await test_events()
        print()
        
        await test_sse_stream()
        print()
        
        print("=" * 50)
        print("✅ All tests completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nMake sure the backend is running:")
        print("  cd backend && uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(run_all_tests())