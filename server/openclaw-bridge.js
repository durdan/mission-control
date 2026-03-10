#!/usr/bin/env node

/**
 * OpenClaw Bridge API
 * 
 * This server provides REST API endpoints by calling OpenClaw CLI commands.
 * It works with OpenClaw running anywhere (local or remote) as long as
 * the OpenClaw CLI is configured to connect to it.
 */

const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const { promisify } = require('util');
const WebSocket = require('ws');

const execAsync = promisify(exec);
const app = express();
const PORT = process.env.BRIDGE_PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Helper to execute OpenClaw commands
async function runOpenClawCommand(command) {
  try {
    const { stdout, stderr } = await execAsync(`openclaw ${command}`);
    return { success: true, output: stdout, error: stderr };
  } catch (error) {
    return { success: false, output: '', error: error.message };
  }
}

// Parse OpenClaw sessions output
function parseSessions(output) {
  const lines = output.split('\n').filter(line => line.trim());
  const sessions = [];
  
  // Skip header lines
  const dataLines = lines.slice(3); // Skip "Session store:", "Sessions listed:", "Kind Key..."
  
  for (const line of dataLines) {
    if (!line.trim()) continue;
    
    // Parse session line (example: "direct agent:main:main just now deepseek/deepseek-chat 36k/164k (22%) system id:...")
    const parts = line.split(/\s+/);
    if (parts.length >= 4) {
      const [kind, key, ...rest] = parts;
      const ageIndex = rest.findIndex(p => p === 'now' || p === 'ago');
      const age = rest.slice(0, ageIndex + 1).join(' ');
      const model = rest[ageIndex + 1] || '';
      
      // Extract session ID from the line
      const idMatch = line.match(/id:([a-f0-9-]+)/);
      const id = idMatch ? idMatch[1] : key;
      
      sessions.push({
        id,
        kind,
        key,
        age,
        model,
        status: 'active',
        raw: line
      });
    }
  }
  
  return sessions;
}

// API Endpoints

// Get OpenClaw status and configuration
app.get('/api/status', async (req, res) => {
  const statusResult = await runOpenClawCommand('gateway status');
  const sessionsResult = await runOpenClawCommand('sessions');
  
  res.json({
    gateway: statusResult.output,
    sessions: parseSessions(sessionsResult.output),
    connected: statusResult.success
  });
});

// Handle enrollment/token configuration
app.post('/api/enroll', async (req, res) => {
  const { token, endpoint } = req.body;
  
  if (!token) {
    return res.status(400).json({ error: 'Token is required for enrollment' });
  }
  
  // Set the token in OpenClaw config
  const result = await runOpenClawCommand(`config set gateway.token "${token}"`);
  
  if (result.success) {
    res.json({ 
      success: true, 
      message: 'Successfully enrolled with new token',
      output: result.output 
    });
  } else {
    res.status(500).json({ 
      error: 'Failed to enroll', 
      details: result.error 
    });
  }
});

// Get sessions (agents)
app.get('/api/sessions', async (req, res) => {
  const result = await runOpenClawCommand('sessions');
  if (result.success) {
    const sessions = parseSessions(result.output);
    res.json({ 
      sessions,
      count: sessions.length,
      raw: result.output 
    });
  } else {
    res.status(500).json({ error: result.error });
  }
});

// Get agents (alias for sessions)
app.get('/api/agents', async (req, res) => {
  const result = await runOpenClawCommand('sessions');
  if (result.success) {
    const sessions = parseSessions(result.output);
    // Transform sessions into agent format for UI compatibility
    const agents = sessions.map(session => ({
      id: session.id,
      name: session.key.split(':').pop() || session.key,
      role: session.kind,
      status: 'active',
      type: session.kind === 'direct' ? 'specialist' : 'orchestrator',
      model: session.model,
      session: session
    }));
    res.json({ agents });
  } else {
    res.status(500).json({ error: result.error });
  }
});

// Create a task
app.post('/api/tasks', async (req, res) => {
  const { description, agent = 'main', priority = 'P2' } = req.body;
  
  if (!description) {
    return res.status(400).json({ error: 'Task description is required' });
  }
  
  const result = await runOpenClawCommand(`task "${description}" --agent ${agent}`);
  if (result.success) {
    res.json({ 
      success: true, 
      message: 'Task created',
      output: result.output 
    });
  } else {
    res.status(500).json({ error: result.error });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    message: 'OpenClaw Bridge API',
    openclaw: 'Connected via CLI'
  });
});

// WebSocket for real-time updates
const wss = new WebSocket.Server({ port: 3002 });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log('Client connected to WebSocket');
  
  // Send initial connection confirmation
  ws.send(JSON.stringify({ type: 'connected' }));
  
  // Poll OpenClaw for updates every 5 seconds
  const interval = setInterval(async () => {
    if (ws.readyState === WebSocket.OPEN) {
      const result = await runOpenClawCommand('sessions');
      if (result.success) {
        const sessions = parseSessions(result.output);
        ws.send(JSON.stringify({
          type: 'update',
          data: { sessions }
        }));
      }
    }
  }, 5000);
  
  ws.on('close', () => {
    clearInterval(interval);
    clients.delete(ws);
    console.log('Client disconnected from WebSocket');
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`
🔌 OpenClaw Bridge API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 REST API: http://localhost:${PORT}
🔄 WebSocket: ws://localhost:3002
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bridging Mission Control to OpenClaw CLI
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down bridge...');
  wss.clients.forEach(client => client.close());
  process.exit(0);
});