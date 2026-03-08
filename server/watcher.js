#!/usr/bin/env node

/**
 * LESSON LEARNED: This is a WATCHER only. It reads OpenClaw's files.
 * It does NOT create tasks, route them, or manage agents.
 * OpenClaw does all that. We just watch and display.
 */

const chokidar = require('chokidar');
const fs = require('fs').promises;
const path = require('path');
const WebSocket = require('ws');
const logger = require('./utils/logger');

class OpenClawWatcher {
  constructor() {
    // WebSocket server for UI updates only
    this.wss = new WebSocket.Server({ port: 3002 });
    this.clients = new Set();
    
    // Paths to watch - OpenClaw's actual workspace directories
    this.watchPaths = [
      // Main workspace
      '/Users/durdan/.openclaw/workspace/**/*.json',
      '/Users/durdan/.openclaw/workspace/**/*.md',
      
      // Agent workspaces
      '/Users/durdan/.openclaw/marketing/*/inbox/*.json',
      '/Users/durdan/.openclaw/marketing/*/memory/*.md',
      
      // Engineering workspaces
      '/Users/durdan/engineering/*/inbox/*.json',
      '/Users/durdan/engineering/*/memory/*.md',
      
      // Orchestrator workspaces
      '/Users/durdan/orchestrators/*/inbox/*.json',
      '/Users/durdan/orchestrators/*/memory/*.md',
      
      // Other team workspaces
      '/Users/durdan/growth/*/inbox/*.json',
      '/Users/durdan/product/*/inbox/*.json',
      '/Users/durdan/ops/*/inbox/*.json'
    ];
    
    // Cache of current state (for UI display only)
    this.state = {
      tasks: [],
      agents: [],
      activities: []
    };
  }

  async start() {
    logger.info('🔍 Starting OpenClaw Workspace Watcher...');
    logger.info('PRINCIPLE: Read only. Watch only. Display only.');
    
    // Setup WebSocket for UI updates
    this.setupWebSocket();
    
    // Initial scan of workspaces
    await this.scanWorkspaces();
    
    // Start watching for changes
    this.startWatching();
    
    logger.info('✅ Watcher started. Monitoring OpenClaw workspaces.');
  }

  setupWebSocket() {
    this.wss.on('connection', (ws) => {
      this.clients.add(ws);
      
      // Send current state to new client
      ws.send(JSON.stringify({
        type: 'initial',
        data: this.state
      }));
      
      ws.on('close', () => {
        this.clients.delete(ws);
      });
    });
  }

  startWatching() {
    // Watch OpenClaw workspace directories
    const watcher = chokidar.watch(this.watchPaths, {
      persistent: true,
      ignoreInitial: true,
      depth: 5
    });
    
    // File added or changed
    watcher.on('add', (filePath) => this.handleFileChange(filePath, 'added'));
    watcher.on('change', (filePath) => this.handleFileChange(filePath, 'changed'));
    watcher.on('unlink', (filePath) => this.handleFileChange(filePath, 'removed'));
    
    logger.info(`Watching paths:`, this.watchPaths);
  }

  async handleFileChange(filePath, event) {
    logger.debug(`File ${event}: ${filePath}`);
    
    try {
      // Determine file type
      if (filePath.includes('/inbox/') && filePath.endsWith('.json')) {
        await this.handleTaskFile(filePath, event);
      } else if (filePath.includes('/memory/') && filePath.endsWith('.md')) {
        await this.handleMemoryFile(filePath, event);
      } else if (filePath.endsWith('agent.json')) {
        await this.handleAgentFile(filePath, event);
      }
      
      // Broadcast changes to UI
      this.broadcastState();
    } catch (error) {
      logger.error(`Error handling file ${filePath}:`, error);
    }
  }

  async handleTaskFile(filePath, event) {
    if (event === 'removed') {
      // Remove task from cache
      const taskId = path.basename(filePath, '.json');
      this.state.tasks = this.state.tasks.filter(t => t.id !== taskId);
      return;
    }
    
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const task = JSON.parse(content);
      
      // Extract agent from path
      const pathParts = filePath.split('/');
      const agentIndex = pathParts.findIndex(p => p === 'inbox') - 1;
      const agentId = pathParts[agentIndex];
      
      // Add metadata for UI display
      task.agent = agentId;
      task.file = filePath;
      task.lastModified = new Date().toISOString();
      
      // Update cache
      const existingIndex = this.state.tasks.findIndex(t => t.id === task.id);
      if (existingIndex >= 0) {
        this.state.tasks[existingIndex] = task;
      } else {
        this.state.tasks.push(task);
      }
      
      logger.info(`Task ${task.id} ${event} for agent ${agentId}`);
    } catch (error) {
      logger.error(`Failed to parse task file ${filePath}:`, error);
    }
  }

  async handleMemoryFile(filePath, event) {
    // Parse memory files for activity feed
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const agentId = this.extractAgentFromPath(filePath);
      
      // Extract recent activities (last 10 lines for activity feed)
      const lines = content.split('\n').filter(line => line.trim());
      const recentActivity = {
        agent: agentId,
        timestamp: new Date().toISOString(),
        entries: lines.slice(-10)
      };
      
      // Update activity cache
      this.state.activities.unshift(recentActivity);
      this.state.activities = this.state.activities.slice(0, 100); // Keep last 100
      
    } catch (error) {
      // Memory file might not exist yet
      logger.debug(`Memory file not ready: ${filePath}`);
    }
  }

  async handleAgentFile(filePath, event) {
    // Update agent configuration
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const agent = JSON.parse(content);
      
      // Update agent cache
      const existingIndex = this.state.agents.findIndex(a => a.id === agent.id);
      if (existingIndex >= 0) {
        this.state.agents[existingIndex] = agent;
      } else {
        this.state.agents.push(agent);
      }
      
      logger.info(`Agent ${agent.id} configuration updated`);
    } catch (error) {
      logger.error(`Failed to parse agent file ${filePath}:`, error);
    }
  }

  async scanWorkspaces() {
    logger.info('Performing initial workspace scan...');
    
    // Scan for existing tasks
    const taskPatterns = [
      '/Users/durdan/.openclaw/workspace/**/inbox/*.json',
      '/Users/durdan/.openclaw/marketing/*/inbox/*.json',
      '/Users/durdan/engineering/*/inbox/*.json',
      '/Users/durdan/orchestrators/*/inbox/*.json',
      '/Users/durdan/growth/*/inbox/*.json',
      '/Users/durdan/product/*/inbox/*.json',
      '/Users/durdan/ops/*/inbox/*.json'
    ];
    
    // This is a simplified scan - in production, use glob
    this.state.tasks = [];
    
    // Load agent configurations from openclaw.json
    try {
      const openclawConfig = await fs.readFile('/Users/durdan/.openclaw/openclaw.json', 'utf8');
      const config = JSON.parse(openclawConfig);
      this.state.agents = config.agents?.list || [];
    } catch (error) {
      logger.error('Failed to load openclaw.json:', error);
    }
    
    logger.info(`Initial scan complete. Found ${this.state.agents.length} agents.`);
  }

  extractAgentFromPath(filePath) {
    const pathParts = filePath.split('/');
    
    // Find the agent directory (before inbox/memory)
    for (let i = pathParts.length - 2; i >= 0; i--) {
      if (pathParts[i + 1] === 'inbox' || pathParts[i + 1] === 'memory') {
        return pathParts[i];
      }
    }
    
    return 'unknown';
  }

  broadcastState() {
    const message = JSON.stringify({
      type: 'update',
      data: this.state,
      timestamp: new Date().toISOString()
    });
    
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  // NO task creation methods
  // NO agent management methods  
  // NO routing logic
  // ONLY watching and broadcasting
}

// Start the watcher
const watcher = new OpenClawWatcher();
watcher.start().catch(console.error);

// Graceful shutdown
process.on('SIGINT', () => {
  logger.info('Shutting down watcher...');
  process.exit(0);
});

/**
 * REMEMBER: 
 * - This watcher is READ-ONLY
 * - It doesn't create or modify anything
 * - It just watches OpenClaw's files and tells the UI what changed
 * - OpenClaw handles all the actual work
 */