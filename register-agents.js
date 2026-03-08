#!/usr/bin/env node

// Script to register all Mission Control agents with OpenClaw

const fs = require('fs').promises;
const path = require('path');

const OPENCLAW_DIR = path.join(process.env.HOME, '.openclaw');
const AGENTS_DIR = path.join(OPENCLAW_DIR, 'agents');

// All our agents with their configurations
const agents = [
  // Orchestrators
  {
    id: 'ceo-atlas',
    name: 'CEO Atlas',
    role: 'Global Orchestrator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/orchestrators/ceo-atlas'
  },
  {
    id: 'engineering-atlas',
    name: 'Engineering Atlas',
    role: 'SDLC Orchestrator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/orchestrators/engineering-atlas'
  },
  {
    id: 'growth-atlas',
    name: 'Growth Atlas',
    role: 'Marketing & Growth Orchestrator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/orchestrators/growth-atlas'
  },
  {
    id: 'product-atlas',
    name: 'Product Atlas',
    role: 'Discovery Orchestrator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/orchestrators/product-atlas'
  },
  {
    id: 'ops-atlas',
    name: 'Ops Atlas',
    role: 'Reliability & Compliance Orchestrator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/orchestrators/ops-atlas'
  },
  
  // Engineering Team
  {
    id: 'forge',
    name: 'Forge',
    role: 'Full-Stack Developer',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/engineering/forge'
  },
  {
    id: 'tess',
    name: 'Tess',
    role: 'QA/Test Engineer',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/engineering/tess'
  },
  {
    id: 'arc',
    name: 'Arc',
    role: 'Software Architect',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/engineering/arc'
  },
  {
    id: 'guardian',
    name: 'Guardian',
    role: 'Security Engineer',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/engineering/guardian'
  },
  {
    id: 'shield',
    name: 'Shield',
    role: 'Code Reviewer',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/engineering/shield'
  },
  {
    id: 'docsmith',
    name: 'DocSmith',
    role: 'Documentation Engineer',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/engineering/docsmith'
  },
  
  // Growth Team (New)
  {
    id: 'beacon',
    name: 'Beacon',
    role: 'Content Creator',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/growth/beacon'
  },
  {
    id: 'orbit',
    name: 'Orbit',
    role: 'SEO Specialist',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/growth/orbit'
  },
  {
    id: 'pulse',
    name: 'Pulse',
    role: 'CRM Manager',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/growth/pulse'
  },
  {
    id: 'relay',
    name: 'Relay',
    role: 'PR Specialist',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/growth/relay'
  },
  {
    id: 'lumen',
    name: 'Lumen',
    role: 'Design Support',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/growth/lumen'
  },
  
  // Product Team
  {
    id: 'sage',
    name: 'Sage',
    role: 'Requirements Analyst',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/product/sage'
  },
  {
    id: 'nova',
    name: 'Nova',
    role: 'UX Researcher',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/product/nova'
  },
  {
    id: 'signal',
    name: 'Signal',
    role: 'Analytics Specialist',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/product/signal'
  },
  
  // Ops Team
  {
    id: 'ops-sentinel',
    name: 'Ops Sentinel',
    role: 'Monitoring Specialist',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/ops/sentinel'
  },
  {
    id: 'auditor',
    name: 'Auditor',
    role: 'Compliance Officer',
    model: 'openrouter/anthropic/claude-sonnet-4.5',
    workspace: '/Users/durdan/ops/auditor'
  },
  {
    id: 'responder',
    name: 'Responder',
    role: 'Incident Manager',
    model: 'openrouter/deepseek/deepseek-chat',
    workspace: '/Users/durdan/ops/responder'
  }
];

async function registerAgents() {
  console.log('🚀 Registering Mission Control agents with OpenClaw...\n');
  
  // Create agent directories and configs
  for (const agent of agents) {
    const agentDir = path.join(AGENTS_DIR, agent.id);
    const agentConfig = path.join(agentDir, 'agent.json');
    
    try {
      // Create directory
      await fs.mkdir(agentDir, { recursive: true });
      
      // Write agent config
      await fs.writeFile(agentConfig, JSON.stringify(agent, null, 2));
      
      console.log(`✅ Registered: ${agent.name} (${agent.id})`);
    } catch (error) {
      console.error(`❌ Failed to register ${agent.id}:`, error.message);
    }
  }
  
  // Update openclaw.json to include all agents
  console.log('\n📝 Updating openclaw.json...');
  
  try {
    const openclawPath = path.join(OPENCLAW_DIR, 'openclaw.json');
    const openclawData = await fs.readFile(openclawPath, 'utf8');
    const openclaw = JSON.parse(openclawData);
    
    // Get all agent IDs
    const allAgentIds = agents.map(a => a.id);
    
    // Update main agent's allowed agents
    if (!openclaw.agents) openclaw.agents = {};
    if (!openclaw.agents.list) openclaw.agents.list = [];
    
    const mainAgent = openclaw.agents.list.find(a => a.id === 'main');
    if (mainAgent) {
      if (!mainAgent.subagents) mainAgent.subagents = {};
      if (!mainAgent.subagents.allowAgents) mainAgent.subagents.allowAgents = [];
      
      // Add new agents to allowed list
      const existingAgents = new Set(mainAgent.subagents.allowAgents);
      allAgentIds.forEach(id => existingAgents.add(id));
      mainAgent.subagents.allowAgents = Array.from(existingAgents);
    }
    
    // Add all agents to the list if not present
    for (const agent of agents) {
      const exists = openclaw.agents.list.some(a => a.id === agent.id);
      if (!exists) {
        openclaw.agents.list.push({
          id: agent.id,
          name: agent.name,
          model: agent.model,
          workspace: agent.workspace,
          metadata: {
            role: agent.role
          }
        });
      }
    }
    
    // Save updated config
    await fs.writeFile(openclawPath, JSON.stringify(openclaw, null, 2));
    console.log('✅ Updated openclaw.json with all agents');
    
  } catch (error) {
    console.error('❌ Failed to update openclaw.json:', error.message);
  }
  
  console.log('\n✨ Agent registration complete!');
  console.log('📊 Total agents registered:', agents.length);
  console.log('\n🔄 Restart OpenClaw gateway to see agents in dashboard:');
  console.log('   killall -9 openclaw');
  console.log('   openclaw serve');
}

// Run the registration
registerAgents().catch(console.error);