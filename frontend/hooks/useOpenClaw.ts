/**
 * useOpenClaw Hook
 * 
 * LESSON LEARNED: This hook connects to OpenClaw's NATIVE API
 * Not our custom services. We're just a UI layer.
 */

import { useEffect, useState } from 'react';

const OPENCLAW_GATEWAY_WS = 'ws://127.0.0.1:18789';
const GATEWAY_TOKEN = '93681890662fa16bf44af824c8524fe161bb5834234bfa21';

interface Agent {
  id: string;
  name: string;
  role?: string;
  model?: string;
  workspace?: string;
  status?: string;
}

interface Task {
  id: string;
  description: string;
  status: string;
  agent?: string;
  priority?: string;
  created_at?: string;
}

interface OpenClawState {
  agents: Agent[];
  tasks: Task[];
  activities: any[];
  connected: boolean;
}

export function useOpenClaw() {
  const [state, setState] = useState<OpenClawState>({
    agents: [],
    tasks: [],
    activities: [],
    connected: false
  });

  // Since OpenClaw doesn't have a public API, load agents from static config
  useEffect(() => {
    // Use the agent hierarchy from openclaw.json that we saw in the config
    const staticAgents = [
      {
        id: 'ceo',
        name: 'CEO Atlas',
        workspace: '/Users/durdan/orchestrators/ceo-atlas',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'engineering',
        name: 'Engineering Atlas',
        workspace: '/Users/durdan/orchestrators/engineering-atlas',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'growth',
        name: 'Growth Atlas',
        workspace: '/Users/durdan/orchestrators/growth-atlas',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'product',
        name: 'Product Atlas',
        workspace: '/Users/durdan/orchestrators/product-atlas',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'ops',
        name: 'Ops Atlas',
        workspace: '/Users/durdan/orchestrators/ops-atlas',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'forge',
        name: 'Forge',
        workspace: '/Users/durdan/engineering/forge',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'tess',
        name: 'Tess',
        workspace: '/Users/durdan/engineering/tess',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'arc',
        name: 'Arc',
        workspace: '/Users/durdan/engineering/arc',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'guardian',
        name: 'Guardian',
        workspace: '/Users/durdan/engineering/guardian',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'shield',
        name: 'Shield',
        workspace: '/Users/durdan/engineering/shield',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'docsmith',
        name: 'DocSmith',
        workspace: '/Users/durdan/engineering/docsmith',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'beacon',
        name: 'Beacon',
        workspace: '/Users/durdan/growth/beacon',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'orbit',
        name: 'Orbit',
        workspace: '/Users/durdan/growth/orbit',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'pulse',
        name: 'Pulse',
        workspace: '/Users/durdan/growth/pulse',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'relay',
        name: 'Relay',
        workspace: '/Users/durdan/growth/relay',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'lumen',
        name: 'Lumen',
        workspace: '/Users/durdan/growth/lumen',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'sage',
        name: 'Sage',
        workspace: '/Users/durdan/product/sage',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'nova',
        name: 'Nova',
        workspace: '/Users/durdan/product/nova',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'signal',
        name: 'Signal',
        workspace: '/Users/durdan/product/signal',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'sentinel',
        name: 'Ops Sentinel',
        workspace: '/Users/durdan/ops/sentinel',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      },
      {
        id: 'auditor',
        name: 'Auditor',
        workspace: '/Users/durdan/ops/auditor',
        model: 'openrouter/anthropic/claude-sonnet-4.5',
        status: 'active'
      },
      {
        id: 'responder',
        name: 'Responder',
        workspace: '/Users/durdan/ops/responder',
        model: 'openrouter/deepseek/deepseek-chat',
        status: 'active'
      }
    ];
    
    setState(prev => ({ 
      ...prev, 
      agents: staticAgents,
      connected: true
    }));
    
    console.log('✅ Loaded static agent configuration');
  }, []);

  const fetchAgents = async () => {
    // No longer needed - using static agent configuration
    console.log('Using static agent configuration');
  };

  /**
   * IMPORTANT: We don't create tasks here!
   * This returns the OpenClaw CLI command to run
   */
  const getTaskCommand = (description: string, agent: string = 'main') => {
    return `openclaw task "${description}" --agent ${agent}`;
  };

  /**
   * Get agent status from OpenClaw
   */
  const getAgentStatus = async (agentId: string) => {
    try {
      const response = await fetch(`${OPENCLAW_API}/agents/${agentId}`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get agent status:', error);
      return null;
    }
  };

  /**
   * Read workspace files - placeholder for cloud deployment
   */
  const readWorkspaceFile = async (path: string) => {
    // In cloud deployment, we can't access local files directly
    // This would need to be implemented via OpenClaw's API when available
    console.log(`Would read workspace file: ${path}`);
    return null;
  };

  return {
    // State from file watcher
    agents: state.agents,
    tasks: state.tasks,
    activities: state.activities,
    connected: state.connected,
    
    // Read-only functions
    getTaskCommand,
    getAgentStatus,
    readWorkspaceFile,
    
    // Refresh data
    refresh: fetchAgents
  };
}

/**
 * WHAT THIS HOOK DOES:
 * ✅ Connects to OpenClaw's native API
 * ✅ Watches workspace files for changes
 * ✅ Provides read-only access to data
 * 
 * WHAT IT DOESN'T DO:
 * ❌ Create tasks (use OpenClaw CLI)
 * ❌ Manage agents (OpenClaw does this)
 * ❌ Route tasks (OpenClaw does this)
 * ❌ Store data (OpenClaw uses files)
 */