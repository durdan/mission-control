# Better Architecture for Mission Control

## Current Setup (What We Built)
```
OpenClaw → Files → Bridge API → Mission Control
```
**Problems:** Indirect, read-only, duplicate infrastructure

## Recommended Setup

### Option 1: Direct API Integration
```javascript
// Mission Control connects directly to OpenClaw Gateway
const OPENCLAW_API = 'http://localhost:8000';

// Use OpenClaw's existing endpoints
GET /api/agents        // List agents
POST /api/agents/spawn // Create agent task
GET /api/status        // System status
WS /ws                 // Real-time updates
```

### Option 2: OpenClaw Extension
```
openclaw/
├── extensions/
│   └── mission-control/
│       ├── ui/          # Dashboard UI
│       └── api.js       # Hooks into OpenClaw
```

### Option 3: Enhance OpenClaw Gateway
Add these endpoints to OpenClaw's gateway:
- `/api/hierarchy` - Agent organization
- `/api/metrics` - Performance data
- `/api/tasks/route` - Task delegation

## Migration Path

### Step 1: Keep Current Setup
- Use for monitoring only
- Learn what data you need

### Step 2: Extend OpenClaw Gateway
```javascript
// In OpenClaw gateway
app.get('/api/dashboard/agents', (req, res) => {
  res.json({
    agents: agentManager.getAllAgents(),
    hierarchy: agentManager.getHierarchy(),
    metrics: agentManager.getMetrics()
  });
});
```

### Step 3: Remove Bridge
- Point Mission Control to OpenClaw Gateway
- Delete bridge server
- Use native OpenClaw WebSocket

## The Right Architecture

```
┌──────────────────────────────┐
│     OpenClaw Gateway         │
│  Enhanced with dashboard API  │
│                              │
│  POST /agents/spawn          │ ← Execute agents
│  GET  /dashboard/agents      │ ← Monitor agents
│  GET  /dashboard/metrics     │ ← View metrics
│  WS   /ws                    │ ← Real-time updates
└──────────────┬───────────────┘
               │
               │ Direct connection
               ↓
┌──────────────────────────────┐
│     Mission Control UI       │
│   (Next.js Dashboard)        │
└──────────────────────────────┘
```

## Why This is Better

1. **Single source of truth** - OpenClaw Gateway
2. **Full control** - Can execute agents, not just watch
3. **Real-time** - Use OpenClaw's existing WebSocket
4. **Maintainable** - No sync issues or file watching
5. **Production ready** - Proper API design

## Quick Fix for Now

If you want to keep current setup but make it more useful:

```javascript
// Add to bridge-enhanced.js
app.post('/api/execute', async (req, res) => {
  // Forward to OpenClaw Gateway
  const response = await fetch('http://localhost:8000/api/agents/spawn', {
    method: 'POST',
    body: JSON.stringify(req.body)
  });
  res.json(await response.json());
});
```

This makes Bridge a proxy to OpenClaw, not just a watcher.