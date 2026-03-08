// Mission Control Production Server
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;

// Services
const logger = require('./utils/logger');
const db = require('./services/DatabaseService');
const agentManager = require('./services/AgentManager');
const taskRouter = require('./services/TaskRouter');
const wsService = require('./services/WebSocketService');
const emailProcessor = require('./services/EmailProcessor');

// Create Express app
const app = express();
const PORT = process.env.PORT || 3001;
const WS_PORT = process.env.WS_PORT || 3002;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001'],
  credentials: true
}));

// Request logging
app.use((req, res, next) => {
  logger.http(`${req.method} ${req.path}`);
  next();
});

// Initialize services
async function initializeServices() {
  try {
    logger.info('Starting Mission Control Server...');
    
    // Create logs directory
    await fs.mkdir(path.join(process.env.HOME, '.openclaw/logs'), { recursive: true });
    
    // Initialize database
    await db.initialize();
    
    // Initialize agent manager
    await agentManager.initialize();
    
    // Initialize WebSocket service
    await wsService.initialize(WS_PORT);
    
    // Setup WebSocket event handlers
    setupWebSocketHandlers();
    
    logger.info('All services initialized successfully');
    
    return true;
  } catch (error) {
    logger.error('Failed to initialize services:', error);
    process.exit(1);
  }
}

// WebSocket event handlers
function setupWebSocketHandlers() {
  wsService.on('client:connected', ({ clientId, ip }) => {
    logger.info(`New WebSocket client: ${clientId} from ${ip}`);
    
    // Send initial state to new client
    const agents = agentManager.getAllAgents();
    const hierarchy = agentManager.getHierarchy();
    
    wsService.sendToClient(clientId, {
      type: 'initial',
      agents,
      hierarchy
    });
  });
  
  wsService.on('client:disconnected', ({ clientId }) => {
    logger.info(`WebSocket client disconnected: ${clientId}`);
  });
  
  wsService.on('message:task:create', async ({ clientId, data }) => {
    try {
      const result = await taskRouter.routeTask(
        data.description,
        data.priority,
        data.metadata
      );
      
      wsService.sendToClient(clientId, {
        type: 'task:created',
        ...result
      });
      
      // Broadcast to all clients
      wsService.broadcastTaskUpdate(result.task);
    } catch (error) {
      wsService.sendToClient(clientId, {
        type: 'error',
        message: error.message
      });
    }
  });
}

// API Routes

// Health check
app.get('/health', async (req, res) => {
  const dbHealth = await db.healthCheck();
  const agentHealth = await agentManager.healthCheck();
  const wsHealth = wsService.getStatus();
  
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    services: {
      database: dbHealth,
      agents: agentHealth,
      websocket: {
        status: 'healthy',
        clients: wsHealth.connected
      }
    }
  });
});

// Agent endpoints
app.get('/api/agents', async (req, res) => {
  try {
    const agents = agentManager.getAllAgents();
    res.json({ agents });
  } catch (error) {
    logger.error('Error fetching agents:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/agents/:id', async (req, res) => {
  try {
    const agent = agentManager.getAgent(req.params.id);
    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }
    
    // Get additional data from database
    const metrics = await db.getAgentMetrics(req.params.id);
    const tasks = await db.getTasks({ agent_id: req.params.id });
    
    res.json({
      ...agent,
      metrics,
      tasks
    });
  } catch (error) {
    logger.error('Error fetching agent:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/agents/:id/status', async (req, res) => {
  try {
    const { status, currentTask } = req.body;
    const agent = await agentManager.updateAgentStatus(
      req.params.id,
      status,
      currentTask
    );
    
    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }
    
    // Broadcast update
    wsService.broadcastAgentUpdate(agent);
    
    res.json({ agent });
  } catch (error) {
    logger.error('Error updating agent status:', error);
    res.status(500).json({ error: error.message });
  }
});

// Task endpoints
app.post('/api/tasks', async (req, res) => {
  try {
    const { description, priority = 'P2', metadata = {} } = req.body;
    
    if (!description) {
      return res.status(400).json({ error: 'Task description is required' });
    }
    
    const result = await taskRouter.routeTask(description, priority, metadata);
    
    // Log activity
    await db.logActivity(
      result.routing.agentId || 'system',
      'Task created',
      `${result.task.id}: ${description.substring(0, 100)}`
    );
    
    // Broadcast task creation
    wsService.broadcastTaskUpdate(result.task);
    
    res.json(result);
  } catch (error) {
    logger.error('Error creating task:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/tasks', async (req, res) => {
  try {
    const { agent_id, status, limit = 100 } = req.query;
    const filters = {};
    
    if (agent_id) filters.agent_id = agent_id;
    if (status) filters.status = status;
    
    const tasks = await db.getTasks(filters);
    res.json({ tasks: tasks.slice(0, limit) });
  } catch (error) {
    logger.error('Error fetching tasks:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/tasks/:id', async (req, res) => {
  try {
    const updates = req.body;
    await db.updateTask(req.params.id, updates);
    
    const task = await db.get('SELECT * FROM tasks WHERE id = ?', [req.params.id]);
    
    // Broadcast update
    wsService.broadcastTaskUpdate(task);
    
    res.json({ task });
  } catch (error) {
    logger.error('Error updating task:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/tasks/:id/complete', async (req, res) => {
  try {
    const { result } = req.body;
    await taskRouter.completeTask(req.params.id, result);
    
    const task = await db.get('SELECT * FROM tasks WHERE id = ?', [req.params.id]);
    
    // Broadcast completion
    wsService.broadcastTaskUpdate(task);
    
    res.json({ task });
  } catch (error) {
    logger.error('Error completing task:', error);
    res.status(500).json({ error: error.message });
  }
});

// Hierarchy endpoint
app.get('/api/hierarchy', (req, res) => {
  try {
    const hierarchy = agentManager.getHierarchy();
    res.json({ hierarchy });
  } catch (error) {
    logger.error('Error fetching hierarchy:', error);
    res.status(500).json({ error: error.message });
  }
});

// Activity endpoint
app.get('/api/activity', async (req, res) => {
  try {
    const { limit = 100 } = req.query;
    const activities = await db.getActivities(limit);
    res.json({ activities });
  } catch (error) {
    logger.error('Error fetching activities:', error);
    res.status(500).json({ error: error.message });
  }
});

// Metrics endpoints
app.get('/api/metrics', async (req, res) => {
  try {
    const routingMetrics = await taskRouter.getRoutingMetrics();
    const agentHealth = await agentManager.healthCheck();
    const wsStatus = wsService.getStatus();
    
    res.json({
      routing: routingMetrics,
      agents: agentHealth,
      websocket: wsStatus,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('Error fetching metrics:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/metrics/agent/:id', async (req, res) => {
  try {
    const { hours = 24 } = req.query;
    const metrics = await db.getAgentMetrics(req.params.id, null, hours);
    res.json({ metrics });
  } catch (error) {
    logger.error('Error fetching agent metrics:', error);
    res.status(500).json({ error: error.message });
  }
});

// Email processing endpoints
app.post('/api/emails/process', async (req, res) => {
  try {
    const email = req.body;
    
    if (!email.from || !email.subject) {
      return res.status(400).json({ error: 'Email must have from and subject fields' });
    }
    
    // Process single email
    const result = await emailProcessor.processEmail(email);
    
    // Broadcast via WebSocket
    wsService.broadcast({
      type: 'email:processed',
      email: {
        from: email.from,
        mailbox: email.mailbox,
        subject: email.subject
      },
      classification: result.classification,
      routing: result.routing,
      taskId: result.task.id
    }, 'emails');
    
    res.json(result);
  } catch (error) {
    logger.error('Error processing email:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/emails/batch', async (req, res) => {
  try {
    const { emails } = req.body;
    
    if (!Array.isArray(emails)) {
      return res.status(400).json({ error: 'Emails must be an array' });
    }
    
    // Process batch of emails
    const results = await emailProcessor.processEmailBatch(emails);
    
    // Broadcast summary
    wsService.broadcast({
      type: 'email:batch_processed',
      total: emails.length,
      successful: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length
    }, 'emails');
    
    res.json({ results });
  } catch (error) {
    logger.error('Error processing email batch:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/emails/stats', async (req, res) => {
  try {
    const { hours = 24 } = req.query;
    
    // Get email processing statistics
    const tasks = await db.all(`
      SELECT * FROM tasks 
      WHERE created_at > datetime('now', '-${hours} hours')
      AND routing LIKE '%"type":"email"%'
    `);
    
    const stats = {
      total: tasks.length,
      byIntent: {},
      byUrgency: {},
      byMailbox: {},
      averageResponseTime: 0,
      period: `${hours} hours`
    };
    
    // Calculate statistics
    tasks.forEach(task => {
      const metadata = JSON.parse(task.routing || '{}');
      if (metadata.type === 'email') {
        // Count by intent
        const intent = metadata.classification?.intent || 'unknown';
        stats.byIntent[intent] = (stats.byIntent[intent] || 0) + 1;
        
        // Count by urgency
        const urgency = metadata.classification?.urgency || 'unknown';
        stats.byUrgency[urgency] = (stats.byUrgency[urgency] || 0) + 1;
        
        // Count by mailbox
        const mailbox = metadata.originalEmail?.mailbox || 'unknown';
        stats.byMailbox[mailbox] = (stats.byMailbox[mailbox] || 0) + 1;
      }
    });
    
    res.json({ stats });
  } catch (error) {
    logger.error('Error fetching email stats:', error);
    res.status(500).json({ error: error.message });
  }
});

// Approval endpoints
app.get('/api/approvals', async (req, res) => {
  try {
    const approvals = await db.getPendingApprovals();
    res.json({ approvals });
  } catch (error) {
    logger.error('Error fetching approvals:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/approvals', async (req, res) => {
  try {
    const approval = {
      id: `approval_${Date.now()}`,
      ...req.body
    };
    
    await db.createApprovalRequest(approval);
    
    // Broadcast new approval
    wsService.broadcast({
      type: 'approval:requested',
      approval
    }, 'approvals');
    
    res.json({ approval });
  } catch (error) {
    logger.error('Error creating approval:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/approvals/:id', async (req, res) => {
  try {
    const { approver, status, comments } = req.body;
    await db.resolveApproval(req.params.id, approver, status, comments);
    
    // Broadcast resolution
    wsService.broadcast({
      type: 'approval:resolved',
      approvalId: req.params.id,
      status
    }, 'approvals');
    
    res.json({ success: true });
  } catch (error) {
    logger.error('Error resolving approval:', error);
    res.status(500).json({ error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

async function shutdown() {
  logger.info('Received shutdown signal, closing gracefully...');
  
  // Close WebSocket connections
  wsService.close();
  
  // Close database
  await db.close();
  
  // Close server
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
  
  // Force close after 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

// Start server
let server;
initializeServices().then(() => {
  server = app.listen(PORT, () => {
    logger.info(`
🚀 Mission Control Server Started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 API Server: http://localhost:${PORT}
🔌 WebSocket:  ws://localhost:${WS_PORT}
📊 Dashboard:  http://localhost:3000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    `);
  });
}).catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});