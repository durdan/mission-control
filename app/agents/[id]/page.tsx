'use client';

import { useParams, useRouter } from 'next/navigation';
import { useOpenClaw } from '@/hooks/useOpenClaw';
import { FiChevronLeft, FiCpu, FiFolder, FiGitBranch, FiBox, FiFileText, FiActivity } from 'react-icons/fi';
import { useEffect, useState } from 'react';

// Agent hierarchy configuration
const agentHierarchy = {
  'ceo': {
    role: 'Global Orchestrator',
    description: 'Top-level orchestrator that delegates to domain orchestrators',
    subagents: ['engineering', 'growth', 'product', 'ops']
  },
  'engineering': {
    role: 'SDLC Orchestrator',
    description: 'Manages software development lifecycle and technical tasks',
    subagents: ['forge', 'tess', 'arc', 'guardian', 'shield', 'docsmith']
  },
  'growth': {
    role: 'Marketing & Growth Orchestrator',
    description: 'Manages marketing, content, and growth initiatives',
    subagents: ['beacon', 'orbit', 'pulse', 'relay', 'lumen']
  },
  'product': {
    role: 'Discovery Orchestrator',
    description: 'Manages product discovery, research, and analytics',
    subagents: ['sage', 'nova', 'signal']
  },
  'ops': {
    role: 'Reliability & Compliance Orchestrator',
    description: 'Manages operations, monitoring, and compliance',
    subagents: ['sentinel', 'auditor', 'responder']
  },
  // Specialists
  'forge': { role: 'Full-Stack Developer', description: 'Code generation and implementation' },
  'tess': { role: 'QA/Test Engineer', description: 'Testing and quality assurance' },
  'arc': { role: 'Software Architect', description: 'Architecture and design' },
  'guardian': { role: 'Security Engineer', description: 'Security review and hardening' },
  'shield': { role: 'Code Reviewer', description: 'Code review and standards' },
  'docsmith': { role: 'Documentation Engineer', description: 'Technical documentation' },
  'beacon': { role: 'Content Creator', description: 'Content creation and copywriting' },
  'orbit': { role: 'SEO Specialist', description: 'Search optimization' },
  'pulse': { role: 'CRM Manager', description: 'Customer relationship management' },
  'relay': { role: 'PR Specialist', description: 'Public relations and communications' },
  'lumen': { role: 'Design Support', description: 'Visual design and branding' },
  'sage': { role: 'Requirements Analyst', description: 'Requirements gathering and analysis' },
  'nova': { role: 'UX Researcher', description: 'User experience research' },
  'signal': { role: 'Analytics Specialist', description: 'Data analytics and insights' },
  'sentinel': { role: 'Monitoring Specialist', description: 'System monitoring and alerts' },
  'auditor': { role: 'Compliance Officer', description: 'Compliance and audit' },
  'responder': { role: 'Incident Manager', description: 'Incident response and management' }
};

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { agents, tasks, readWorkspaceFile } = useOpenClaw();
  const [identity, setIdentity] = useState<string | null>(null);
  const [memory, setMemory] = useState<string | null>(null);
  
  const agentId = params.id as string;
  const agent = agents.find(a => a.id === agentId);
  const agentInfo = agentHierarchy[agentId as keyof typeof agentHierarchy];
  
  // Load agent identity file
  useEffect(() => {
    if (agent?.workspace) {
      const loadIdentity = async () => {
        try {
          const identityPath = agent.workspace.replace('/Users/durdan/', '') + '/IDENTITY.md';
          const content = await readWorkspaceFile(identityPath);
          setIdentity(content);
        } catch (error) {
          console.log('No identity file found');
        }
      };
      loadIdentity();
    }
  }, [agent, readWorkspaceFile]);

  // Load recent memory
  useEffect(() => {
    if (agent?.workspace) {
      const loadMemory = async () => {
        try {
          const today = new Date().toISOString().split('T')[0];
          const memoryPath = agent.workspace.replace('/Users/durdan/', '') + `/memory/${today}.md`;
          const content = await readWorkspaceFile(memoryPath);
          setMemory(content);
        } catch (error) {
          console.log('No memory file for today');
        }
      };
      loadMemory();
    }
  }, [agent, readWorkspaceFile]);

  // Get tasks for this agent
  const agentTasks = tasks.filter(t => t.agent === agentId);
  
  // Get subagent details
  const subagentDetails = agentInfo?.subagents?.map(subId => {
    const subAgent = agents.find(a => a.id === subId);
    const subInfo = agentHierarchy[subId as keyof typeof agentHierarchy];
    return {
      ...subAgent,
      role: subInfo?.role,
      description: subInfo?.description,
      taskCount: tasks.filter(t => t.agent === subId).length
    };
  });

  if (!agent) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6">
        <div className="text-center py-12">
          <p className="text-gray-400">Agent not found</p>
          <button
            onClick={() => router.push('/agents')}
            className="mt-4 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
          >
            Back to Agents
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/agents')}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-4"
        >
          <FiChevronLeft /> Back to Agents
        </button>
        
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">{agent.name}</h1>
              <p className="text-xl text-blue-400">{agentInfo?.role}</p>
              <p className="text-gray-400 mt-2">{agentInfo?.description}</p>
            </div>
            <div className="text-right">
              <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                {agent.status || 'Active'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Model Information */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <FiCpu className="text-blue-400" />
            <h2 className="text-xl font-semibold">Model Configuration</h2>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-gray-400">Model:</span>
              <p className="font-mono text-sm mt-1">{agent.model || 'Not specified'}</p>
            </div>
            <div>
              <span className="text-gray-400">Provider:</span>
              <p className="text-sm mt-1">
                {agent.model?.includes('anthropic') ? 'Anthropic Claude' : 
                 agent.model?.includes('deepseek') ? 'DeepSeek' : 'OpenRouter'}
              </p>
            </div>
          </div>
        </div>

        {/* Workspace Information */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <FiFolder className="text-green-400" />
            <h2 className="text-xl font-semibold">Workspace</h2>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-gray-400">Path:</span>
              <p className="font-mono text-xs mt-1 break-all">{agent.workspace}</p>
            </div>
            <div className="flex gap-4">
              <div>
                <span className="text-gray-400">Active Tasks:</span>
                <p className="text-2xl font-bold text-yellow-400">{agentTasks.length}</p>
              </div>
              <div>
                <span className="text-gray-400">Completed:</span>
                <p className="text-2xl font-bold text-green-400">
                  {agentTasks.filter(t => t.status === 'completed').length}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Subagents Hierarchy */}
      {subagentDetails && subagentDetails.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <FiGitBranch className="text-purple-400" />
            <h2 className="text-xl font-semibold">Subagents ({subagentDetails.length})</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {subagentDetails.map(sub => (
              <div
                key={sub?.id}
                onClick={() => router.push(`/agents/${sub?.id}`)}
                className="bg-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-600 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold">{sub?.name}</h3>
                  <span className="text-xs px-2 py-1 bg-gray-800 rounded">
                    {sub?.taskCount || 0} tasks
                  </span>
                </div>
                <p className="text-sm text-blue-400">{sub?.role}</p>
                <p className="text-xs text-gray-400 mt-1">{sub?.description}</p>
                <div className="mt-3">
                  <span className="text-xs text-gray-500">Model:</span>
                  <p className="text-xs font-mono truncate">{sub?.model}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Identity Section */}
      {identity && (
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <FiFileText className="text-yellow-400" />
            <h2 className="text-xl font-semibold">Identity</h2>
          </div>
          <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-900 p-4 rounded max-h-96 overflow-y-auto">
            {identity}
          </pre>
        </div>
      )}

      {/* Recent Activity */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <FiActivity className="text-orange-400" />
          <h2 className="text-xl font-semibold">Recent Tasks</h2>
        </div>
        {agentTasks.length > 0 ? (
          <div className="space-y-3">
            {agentTasks.slice(0, 5).map(task => (
              <div key={task.id} className="bg-gray-700 rounded p-3">
                <div className="flex justify-between items-start mb-1">
                  <span className={`text-xs px-2 py-1 rounded ${
                    task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    task.status === 'in_progress' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-600 text-gray-400'
                  }`}>
                    {task.status}
                  </span>
                  <span className="text-xs text-gray-500">
                    {task.id.split('_')[1]?.substring(0, 6)}
                  </span>
                </div>
                <p className="text-sm mt-2">{task.description}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No tasks assigned</p>
        )}
      </div>

      {/* OpenClaw Commands */}
      <div className="mt-8 bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Quick Commands</h2>
        <div className="space-y-2">
          <div className="bg-gray-900 rounded p-3">
            <p className="text-xs text-gray-400 mb-1">Assign task to this agent:</p>
            <code className="text-sm text-green-400">
              openclaw task "Your task description" --agent {agentId}
            </code>
          </div>
          <div className="bg-gray-900 rounded p-3">
            <p className="text-xs text-gray-400 mb-1">Check agent status:</p>
            <code className="text-sm text-green-400">
              openclaw agent status {agentId}
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}