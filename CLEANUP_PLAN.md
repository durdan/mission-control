# Mission Control Cleanup Plan

## Current Problem
We built duplicate functionality instead of using OpenClaw's native capabilities. Mission Control should be a **thin UI layer** that visualizes OpenClaw's existing data, not a separate system.

---

## What to Keep ✅
Mission Control should ONLY be:

### 1. **Kanban Board UI**
- Visual representation of tasks from OpenClaw's workspace files
- Drag-and-drop interface for task status updates
- Real-time updates by watching OpenClaw's file system

### 2. **Hierarchy Visualization** 
- Interactive tree view of agent relationships
- Read from openclaw.json configuration
- No custom agent management

### 3. **Dashboard UI**
- Metrics visualization from OpenClaw's logs
- Activity feed from OpenClaw's memory files
- Status indicators from agent workspaces

### 4. **File Watcher Service**
- Watch OpenClaw workspace directories
- Detect changes in task files
- Update UI when files change

---

## What to Remove ❌

### Services to Delete:
1. **AgentManager.js** - OpenClaw manages agents natively
2. **TaskRouter.js** - OpenClaw routes tasks via subagents config
3. **DatabaseService.js** - OpenClaw uses file-based storage
4. **EmailProcessor.js** - Should be an OpenClaw skill, not custom service
5. **WebSocketService.js** - Use file watching instead

### Database to Remove:
- `/Users/durdan/.openclaw/tasks.db` - Use OpenClaw's workspace files

### Custom Endpoints to Remove:
- All `/api/agents/*` - Use OpenClaw's API
- All `/api/tasks/*` - Read from workspace files
- All custom task creation - Use OpenClaw commands

---

## New Architecture

```
┌─────────────────────────────────────────┐
│         OpenClaw Native System          │
├─────────────────────────────────────────┤
│ • Agent Management (openclaw.json)      │
│ • Task Routing (subagents config)       │
│ • File-based Storage (workspaces)       │
│ • Heartbeat Scheduler                   │
│ • Telegram/WhatsApp Interface           │
└─────────────────────────────────────────┘
                    ↑
                    │ Reads files
                    │ No custom APIs
                    ↓
┌─────────────────────────────────────────┐
│      Mission Control (Thin UI)          │
├─────────────────────────────────────────┤
│ • Kanban Board (visualize tasks)        │
│ • Hierarchy View (show agent tree)      │
│ • Dashboard (display metrics)           │
│ • File Watcher (detect changes)         │
└─────────────────────────────────────────┘
```

---

## Implementation Steps

### Phase 1: Setup File Watching (Day 1)
```javascript
// New: server/watcher.js
const chokidar = require('chokidar');

// Watch OpenClaw workspace directories
const watcher = chokidar.watch([
  '/Users/durdan/.openclaw/workspace/**/*.json',
  '/Users/durdan/.openclaw/marketing/*/inbox/*.json',
  '/Users/durdan/engineering/*/inbox/*.json',
  '/Users/durdan/orchestrators/*/inbox/*.json'
]);

watcher.on('change', (path) => {
  // Parse task file
  // Update UI via WebSocket
});
```

### Phase 2: Refactor Kanban (Day 1)
- Remove database queries
- Read tasks directly from workspace directories
- Parse task JSON files
- Display in Kanban columns based on status

### Phase 3: Use OpenClaw Commands (Day 2)
```bash
# Instead of custom API:
POST /api/tasks/create

# Use OpenClaw native:
openclaw task "Build feature X" --agent ceo-atlas
```

### Phase 4: Remove Custom Services (Day 2)
```bash
# Delete these files:
rm server/services/AgentManager.js
rm server/services/TaskRouter.js
rm server/services/DatabaseService.js
rm server/services/EmailProcessor.js
rm -rf /Users/durdan/.openclaw/tasks.db
```

### Phase 5: Simplify Server (Day 3)
```javascript
// New simplified server/index.js
const express = require('express');
const chokidar = require('chokidar');
const ws = require('ws');

const app = express();

// Only endpoints needed:
app.get('/api/workspace/tasks', readTaskFiles);
app.get('/api/workspace/agents', readAgentConfigs);
app.get('/api/workspace/metrics', readMemoryFiles);

// File watcher broadcasts changes
watcher.on('change', broadcastUpdate);
```

---

## Task File Format (OpenClaw Native)

```javascript
// /Users/durdan/orchestrators/ceo-atlas/inbox/task_001.json
{
  "id": "task_001",
  "description": "Build OAuth2 feature",
  "status": "pending",
  "assigned_to": "engineering-atlas",
  "created_at": "2024-03-08T10:00:00Z",
  "priority": "P1"
}

// When engineering-atlas processes:
// /Users/durdan/orchestrators/engineering-atlas/inbox/task_001.json
// /Users/durdan/engineering/forge/inbox/subtask_001.json
// /Users/durdan/engineering/guardian/inbox/subtask_002.json
```

---

## Benefits of This Approach

### What We Gain:
1. **True OpenClaw Integration** - Using native capabilities
2. **Simplified Architecture** - 90% less custom code
3. **File-based Truth** - No database sync issues
4. **Native Agent Communication** - Via workspace files
5. **Automatic Task Routing** - OpenClaw handles delegation

### What We Lose:
- Custom routing logic (OpenClaw does this better)
- SQL database (files are OpenClaw's database)
- Complex services (unnecessary abstraction)

---

## File Structure After Cleanup

```
mission-control/
├── app/
│   ├── kanban/         # Kanban UI component
│   ├── hierarchy/      # Agent tree visualization
│   └── page.tsx        # Dashboard
├── server/
│   ├── watcher.js      # File system watcher
│   └── index.js        # Minimal Express server
├── hooks/
│   └── useWorkspace.ts # Hook to read workspace files
└── package.json        # Only Express, Chokidar, WS

# Deleted:
# - server/services/*    (all custom services)
# - server/bridge*.js    (custom bridge)
# - database connections
# - task routing logic
```

---

## Migration Path

### Week 1: Parallel Running
- Keep existing system running
- Build file watcher alongside
- Test reading from workspaces

### Week 2: Switch Over
- Point Kanban to file data
- Remove database calls
- Use OpenClaw commands

### Week 3: Cleanup
- Delete unused services
- Remove database
- Simplify codebase

---

## Success Criteria

✅ **Mission Control becomes a viewer, not a controller**
✅ **All task management via OpenClaw commands**
✅ **No duplicate agent management**
✅ **File watching replaces WebSocket complexity**
✅ **80% code reduction**

---

## Commands to Use Instead

### Before (Custom):
```javascript
// Our custom way
await taskRouter.createTask(...)
await agentManager.updateAgent(...)
```

### After (OpenClaw Native):
```bash
# OpenClaw native way
openclaw task "description" --agent ceo-atlas
openclaw agent status forge

# Tasks appear in workspace files
# Mission Control watches and displays
```

---

## Summary

Mission Control should be like a **dashboard in a car** - it shows you speed, fuel, and temperature, but it doesn't have its own engine. OpenClaw is the engine; Mission Control is just the display.

**Core Principle**: Read, don't write. Watch, don't control. Display, don't process.