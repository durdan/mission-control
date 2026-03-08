#!/usr/bin/env node

/**
 * Mission Control Clean Server
 * 
 * LESSON LEARNED: This server ONLY:
 * 1. Serves the Next.js UI
 * 2. Proxies requests to OpenClaw's native API
 * 3. Runs the file watcher
 * 
 * It does NOT:
 * - Manage agents (OpenClaw does this)
 * - Route tasks (OpenClaw does this)
 * - Store data (OpenClaw uses files)
 * - Process emails (Should be OpenClaw skill)
 */

const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Health check (the ONLY custom endpoint we need)
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    message: 'Mission Control UI Server',
    principle: 'Read-only viewer for OpenClaw'
  });
});

/**
 * PROXY all data requests to OpenClaw's native API
 * Instead of our custom endpoints, use OpenClaw's
 */
app.use('/api/openclaw', createProxyMiddleware({
  target: 'http://127.0.0.1:18789',
  changeOrigin: true,
  pathRewrite: {
    '^/api/openclaw': '/api'
  },
  onProxyReq: (proxyReq, req, res) => {
    logger.debug(`Proxying to OpenClaw: ${req.method} ${req.path}`);
  }
}));

/**
 * For task creation, we should use OpenClaw's CLI
 * This endpoint just returns instructions
 */
app.post('/api/tasks', (req, res) => {
  res.status(501).json({
    error: 'Use OpenClaw CLI',
    instructions: 'openclaw task "' + req.body.description + '" --agent main',
    principle: 'Mission Control is read-only. Use OpenClaw commands to create tasks.'
  });
});

/**
 * Static file serving for workspace files
 * Read-only access to OpenClaw's workspace
 */
app.use('/workspace', express.static('/Users/durdan/.openclaw/workspace', {
  dotfiles: 'allow',
  setHeaders: (res, path) => {
    res.set('X-Principle', 'Read-Only Access');
  }
}));

// 404 for everything else
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'This is a thin UI layer. Use OpenClaw API directly.',
    openclaw_api: 'http://127.0.0.1:18789/api'
  });
});

// Start server
const server = app.listen(PORT, () => {
  logger.info(`
🎯 Mission Control Clean Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 UI Server: http://localhost:${PORT}
🔌 OpenClaw API: http://127.0.0.1:18789
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRINCIPLE: Read, don't write.
          Watch, don't control.
          Display, don't process.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('Shutting down UI server...');
  server.close(() => {
    process.exit(0);
  });
});

/**
 * WHAT WE REMOVED:
 * ❌ AgentManager - OpenClaw manages agents
 * ❌ TaskRouter - OpenClaw routes tasks
 * ❌ DatabaseService - OpenClaw uses files
 * ❌ EmailProcessor - Should be OpenClaw skill
 * ❌ WebSocketService - Replaced with simple file watcher
 * ❌ All custom endpoints - Using OpenClaw API
 * 
 * WHAT WE KEPT:
 * ✅ Express server for UI
 * ✅ Proxy to OpenClaw API
 * ✅ Static file serving for workspace
 * ✅ Health check endpoint
 */