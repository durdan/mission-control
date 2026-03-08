# Mission Control - Production Architecture Plan

## Core Principles
- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **KISS**: Keep It Simple, Stupid - Use what OpenClaw provides, don't reinvent
- **DRY**: Don't Repeat Yourself - Leverage existing OpenClaw patterns

## Architecture Overview

### 1. Understanding What We Have

**OpenClaw Native Components:**
- **openclaw-gateway process**: Runs locally, config-driven (not REST API)
- **SQLite databases**: Tasks, memory, agent state
- **File-based communication**: `/comms/` directory for inter-agent messages
- **Configuration system**: `openclaw.json` + hierarchy extensions
- **Agent workspaces**: Isolated directories per agent

**Key Insight**: OpenClaw doesn't have a traditional REST API gateway on port 8000. It's a local process that reads config and manages agents via file system.

### 2. Production Architecture Design

```
┌──────────────────────────────────────────────┐
│              OpenClaw Core                     │
│  ┌──────────────────────────────────────┐     │
│  │  openclaw-gateway (process)          │     │
│  │  - Reads openclaw.json               │     │
│  │  - Spawns agents                     │     │
│  │  - Manages workspaces                │     │
│  └──────────────────────────────────────┘     │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │  File System                         │     │
│  │  /workspace  /agents  /comms         │     │
│  │  tasks.db    memory.db               │     │
│  └──────────────────────────────────────┘     │
└────────────────┬───────────────────────────────┘
                 │
                 │ Native Integration
                 ↓
┌──────────────────────────────────────────────┐
│         Mission Control Service               │
│  ┌──────────────────────────────────────┐     │
│  │  Agent Manager (Core Service)        │     │
│  │  - Reads/writes OpenClaw files       │     │
│  │  - SQLite connection pool            │     │
│  │  - File system watchers              │     │
│  │  - Task routing engine               │     │
│  └──────────────────────────────────────┘     │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │  API Layer (Express)                 │     │
│  │  - REST endpoints                    │     │
│  │  - WebSocket server                  │     │
│  │  - Authentication middleware         │     │
│  └──────────────────────────────────────┘     │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │  Dashboard (Next.js)                 │     │
│  │  - Real-time UI                      │     │
│  │  - Agent visualization               │     │
│  │  - Task management                   │     │
│  └──────────────────────────────────────┘     │
└──────────────────────────────────────────────┘
```

## Implementation Plan (SOLID + KISS)

### Phase 1: Core Services (Week 1)

#### 1.1 Agent Manager Service (Single Responsibility)
```typescript
// services/AgentManager.ts
interface IAgentManager {
  getAgents(): Promise<Agent[]>;
  getAgentStatus(id: string): Promise<AgentStatus>;
  updateAgentStatus(id: string, status: AgentStatus): Promise<void>;
}

class OpenClawAgentManager implements IAgentManager {
  constructor(
    private configPath: string,
    private workspacePath: string,
    private db: Database
  ) {}
  
  // Read from OpenClaw's native files
  async getAgents(): Promise<Agent[]> {
    const config = await this.readConfig();
    const hierarchy = await this.readHierarchy();
    return this.mergeAgentData(config, hierarchy);
  }
}
```

#### 1.2 Task Router (Open/Closed Principle)
```typescript
// services/TaskRouter.ts
interface ITaskRouter {
  route(task: Task): Promise<TaskRouting>;
}

class HierarchicalTaskRouter implements ITaskRouter {
  private strategies: Map<string, IRoutingStrategy>;
  
  // Open for extension via strategies
  registerStrategy(domain: string, strategy: IRoutingStrategy) {
    this.strategies.set(domain, strategy);
  }
  
  async route(task: Task): Promise<TaskRouting> {
    const domain = this.detectDomain(task.description);
    const strategy = this.strategies.get(domain) || new DefaultStrategy();
    return strategy.route(task);
  }
}
```

#### 1.3 File System Observer (Interface Segregation)
```typescript
// services/FileSystemObserver.ts
interface IFileObserver {
  watch(path: string): void;
  onFileChange(callback: FileChangeCallback): void;
}

interface IAgentActivityObserver {
  onAgentActivity(callback: AgentActivityCallback): void;
}

class OpenClawFileObserver implements IFileObserver, IAgentActivityObserver {
  private watcher: FSWatcher;
  
  watch(path: string) {
    this.watcher = chokidar.watch(path, {
      persistent: true,
      ignoreInitial: true
    });
  }
  
  onAgentActivity(callback: AgentActivityCallback) {
    this.watcher.on('change', (path) => {
      const activity = this.parseActivityFromPath(path);
      if (activity) callback(activity);
    });
  }
}
```

### Phase 2: API Layer (Week 2)

#### 2.1 RESTful API (Dependency Inversion)
```typescript
// api/server.ts
class MissionControlAPI {
  constructor(
    private agentManager: IAgentManager,
    private taskRouter: ITaskRouter,
    private database: IDatabase
  ) {
    // Dependencies injected, not created
  }
  
  setupRoutes() {
    // Agent endpoints
    this.app.get('/api/agents', this.getAgents);
    this.app.get('/api/agents/:id', this.getAgent);
    
    // Task endpoints
    this.app.post('/api/tasks', this.createTask);
    this.app.get('/api/tasks', this.getTasks);
    
    // Monitoring
    this.app.get('/api/monitoring', this.getMonitoring);
    
    // WebSocket
    this.setupWebSocket();
  }
}
```

#### 2.2 WebSocket Service (KISS)
```typescript
// api/websocket.ts
class WebSocketService {
  private wss: WebSocket.Server;
  
  constructor(private eventBus: IEventBus) {
    this.wss = new WebSocket.Server({ port: 3002 });
    
    // Simple event forwarding
    eventBus.on('agent:update', (data) => this.broadcast(data));
    eventBus.on('task:created', (data) => this.broadcast(data));
    eventBus.on('activity:new', (data) => this.broadcast(data));
  }
  
  broadcast(data: any) {
    this.wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(data));
      }
    });
  }
}
```

### Phase 3: Database Layer (Week 3)

#### 3.1 Repository Pattern (Single Responsibility)
```typescript
// repositories/TaskRepository.ts
interface ITaskRepository {
  create(task: Task): Promise<Task>;
  findById(id: string): Promise<Task>;
  findByAgent(agentId: string): Promise<Task[]>;
  update(id: string, updates: Partial<Task>): Promise<void>;
}

class SQLiteTaskRepository implements ITaskRepository {
  constructor(private db: Database) {}
  
  async create(task: Task): Promise<Task> {
    const stmt = this.db.prepare(`
      INSERT INTO tasks (id, agent_id, description, priority, status)
      VALUES (?, ?, ?, ?, ?)
    `);
    stmt.run(task.id, task.agentId, task.description, task.priority, 'pending');
    return task;
  }
}
```

### Phase 4: Dashboard UI (Week 4)

#### 4.1 React Components (SOLID)
```typescript
// components/AgentCard.tsx
interface AgentCardProps {
  agent: Agent;
  onTaskCreate: (task: Task) => void;
}

// Single responsibility: Display agent info
const AgentCard: FC<AgentCardProps> = ({ agent, onTaskCreate }) => {
  return (
    <div className="card">
      <AgentStatus agent={agent} />
      <AgentMetrics agent={agent} />
      <CreateTaskButton agentId={agent.id} onCreate={onTaskCreate} />
    </div>
  );
};
```

#### 4.2 State Management (KISS)
```typescript
// hooks/useAgents.ts
export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    // Simple WebSocket connection
    const ws = new WebSocket('ws://localhost:3002');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'agent:update') {
        setAgents(prev => updateAgent(prev, data.agent));
      }
    };
    
    return () => ws.close();
  }, []);
  
  return { agents, connected };
}
```

## Production Deployment

### 1. Service Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  mission-control:
    build: .
    ports:
      - "3000:3000"  # Dashboard
      - "3001:3001"  # API
      - "3002:3002"  # WebSocket
    volumes:
      - ~/.openclaw:/openclaw:rw
    environment:
      - NODE_ENV=production
      - OPENCLAW_PATH=/openclaw
```

### 2. Process Management
```javascript
// pm2.config.js
module.exports = {
  apps: [{
    name: 'mission-control',
    script: 'server/index.js',
    instances: 1,
    autorestart: true,
    watch: false,
    env: {
      NODE_ENV: 'production',
      PORT: 3001
    }
  }]
};
```

### 3. Security Hardening
```typescript
// middleware/auth.ts
export const authenticate = async (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET);
    req.user = payload;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};
```

## Key Design Decisions

### 1. Use OpenClaw's Native Patterns
- ✅ File-based agent communication
- ✅ SQLite for persistence
- ✅ Configuration-driven approach
- ✅ Workspace isolation

### 2. Don't Reinvent the Wheel
- ❌ No custom agent runtime
- ❌ No new communication protocol
- ❌ No separate state management
- ❌ No custom task queue

### 3. Production Ready Features
- ✅ Authentication & authorization
- ✅ Error handling & recovery
- ✅ Monitoring & metrics
- ✅ Scalable architecture
- ✅ Clean separation of concerns

## Migration Path

### Step 1: Refactor Current Bridge
```bash
# Move from single file to modular structure
mission-control/
├── src/
│   ├── services/      # Core business logic
│   ├── api/           # REST & WebSocket
│   ├── repositories/  # Database access
│   └── utils/         # Helpers
├── dashboard/         # Next.js app
└── tests/            # Unit & integration tests
```

### Step 2: Implement Core Services
- AgentManager with OpenClaw file integration
- TaskRouter with hierarchical routing
- FileSystemObserver for real-time updates

### Step 3: Add Production Features
- JWT authentication
- Rate limiting
- Error tracking (Sentry)
- Metrics (Prometheus)

### Step 4: Deploy
- Docker containerization
- PM2 for process management
- Nginx reverse proxy
- SSL/TLS certificates

## Success Metrics

1. **Performance**
   - API response time < 100ms
   - WebSocket latency < 50ms
   - Dashboard load time < 2s

2. **Reliability**
   - 99.9% uptime
   - Auto-recovery from crashes
   - Graceful degradation

3. **Scalability**
   - Support 100+ concurrent agents
   - Handle 1000+ tasks/hour
   - Real-time updates for 50+ dashboard users

## Conclusion

This production architecture:
- **Respects OpenClaw's native design**
- **Follows SOLID principles** for maintainability
- **Keeps it simple (KISS)** by not over-engineering
- **Production-ready** with proper error handling, security, and monitoring
- **Scalable** to handle growth

The key insight is that Mission Control should be a **companion service** that enhances OpenClaw, not a replacement. It reads and writes to OpenClaw's file system and databases, providing a real-time dashboard and API layer while letting OpenClaw handle the actual agent orchestration.