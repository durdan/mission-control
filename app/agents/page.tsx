'use client';

import { useRouter } from 'next/navigation';
import { useOpenClaw } from '@/hooks/useOpenClaw';
import { FiCpu, FiFolder, FiActivity, FiChevronRight, FiGitBranch } from 'react-icons/fi';

// Agent hierarchy for organization
const agentCategories = {
  'Orchestrators': ['ceo-atlas', 'engineering-atlas', 'growth-atlas', 'product-atlas', 'ops-atlas'],
  'Engineering': ['forge', 'tess', 'arc', 'guardian', 'shield', 'docsmith'],
  'Growth': ['beacon', 'orbit', 'pulse', 'relay', 'lumen', 'marketing-lead', 'news-agent', 'social-agent'],
  'Product': ['sage', 'nova', 'signal'],
  'Operations': ['ops-sentinel', 'auditor', 'responder', 'sentinel'],
  'Other': ['digest-agent', 'appstore-agent', 'reddit-agent', 'trustpilot-agent', 'affiliate-agent', 'jobs-agent']
};

const agentRoles: Record<string, string> = {
  'ceo-atlas': 'Global Orchestrator',
  'engineering-atlas': 'SDLC Orchestrator',
  'growth-atlas': 'Marketing & Growth Orchestrator',
  'product-atlas': 'Discovery Orchestrator',
  'ops-atlas': 'Reliability & Compliance Orchestrator',
  'forge': 'Full-Stack Developer',
  'tess': 'QA/Test Engineer',
  'arc': 'Software Architect',
  'guardian': 'Security Engineer',
  'shield': 'Code Reviewer',
  'docsmith': 'Documentation Engineer',
  'beacon': 'Content Creator',
  'orbit': 'SEO Specialist',
  'pulse': 'CRM Manager',
  'relay': 'PR Specialist',
  'lumen': 'Design Support',
  'sage': 'Requirements Analyst',
  'nova': 'UX Researcher',
  'signal': 'Analytics Specialist',
  'ops-sentinel': 'Monitoring Specialist',
  'auditor': 'Compliance Officer',
  'responder': 'Incident Manager',
  'marketing-lead': 'Marketing Lead',
  'news-agent': 'News Monitor',
  'social-agent': 'Social Media Manager',
  'digest-agent': 'Daily Digest Creator',
  'appstore-agent': 'App Store Monitor',
  'reddit-agent': 'Reddit Monitor',
  'trustpilot-agent': 'Review Monitor',
  'affiliate-agent': 'Affiliate Manager',
  'jobs-agent': 'Job Board Monitor',
  'sentinel': 'System Monitor'
};

export default function AgentsPage() {
  const router = useRouter();
  const { agents, tasks, connected } = useOpenClaw();

  const getAgentCategory = (agentId: string) => {
    for (const [category, ids] of Object.entries(agentCategories)) {
      if (ids.includes(agentId)) return category;
    }
    return 'Other';
  };

  const getModelType = (model?: string) => {
    if (!model) return 'Unknown';
    if (model.includes('claude')) return 'Claude';
    if (model.includes('deepseek')) return 'DeepSeek';
    if (model.includes('gpt')) return 'GPT';
    return 'OpenRouter';
  };

  const getModelColor = (model?: string) => {
    if (!model) return 'text-gray-400';
    if (model.includes('claude')) return 'text-purple-400';
    if (model.includes('deepseek')) return 'text-blue-400';
    if (model.includes('gpt')) return 'text-green-400';
    return 'text-gray-400';
  };

  // Group agents by category
  const groupedAgents = agents.reduce((acc, agent) => {
    const category = getAgentCategory(agent.id);
    if (!acc[category]) acc[category] = [];
    acc[category].push(agent);
    return acc;
  }, {} as Record<string, typeof agents>);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Agent Fleet</h1>
            <p className="text-gray-400">
              {agents.length} agents across {Object.keys(groupedAgents).length} departments
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`px-3 py-1 rounded-full text-sm ${
              connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {connected ? '● Connected to OpenClaw' : '● Disconnected'}
            </div>
          </div>
        </div>
      </div>

      {/* Agent Categories */}
      {Object.entries(groupedAgents).map(([category, categoryAgents]) => (
        <div key={category} className="mb-8">
          <h2 className="text-xl font-semibold mb-4 text-gray-300">{category}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {categoryAgents.map(agent => {
              const agentTasks = tasks.filter(t => t.agent === agent.id);
              const role = agentRoles[agent.id];
              const isOrchestrator = category === 'Orchestrators';
              
              return (
                <div
                  key={agent.id}
                  onClick={() => router.push(`/agents/${agent.id}`)}
                  className="bg-gray-800 rounded-lg p-5 cursor-pointer hover:bg-gray-750 transition-all hover:scale-105 border border-gray-700"
                >
                  {/* Agent Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="font-semibold text-white flex items-center gap-2">
                        {agent.name}
                        {isOrchestrator && <FiGitBranch className="text-yellow-400" />}
                      </h3>
                      <p className="text-sm text-blue-400 mt-1">{role}</p>
                    </div>
                    <FiChevronRight className="text-gray-500" />
                  </div>

                  {/* Model Info */}
                  <div className="flex items-center gap-2 mb-3">
                    <FiCpu className={`text-sm ${getModelColor(agent.model)}`} />
                    <span className={`text-xs ${getModelColor(agent.model)}`}>
                      {getModelType(agent.model)}
                    </span>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1">
                      <FiActivity className="text-gray-500" />
                      <span className="text-gray-400">
                        {agentTasks.length} tasks
                      </span>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${
                      agent.status === 'active' ? 'bg-green-500/20 text-green-400' :
                      'bg-gray-700 text-gray-400'
                    }`}>
                      {agent.status || 'idle'}
                    </span>
                  </div>

                  {/* Workspace Path (truncated) */}
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <FiFolder />
                      <span className="truncate">
                        {agent.workspace?.split('/').slice(-2).join('/')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Quick Stats */}
      <div className="mt-12 bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Fleet Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-gray-400 text-sm">Total Agents</p>
            <p className="text-2xl font-bold">{agents.length}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Active Tasks</p>
            <p className="text-2xl font-bold text-yellow-400">{tasks.length}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Claude Models</p>
            <p className="text-2xl font-bold text-purple-400">
              {agents.filter(a => a.model?.includes('claude')).length}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">DeepSeek Models</p>
            <p className="text-2xl font-bold text-blue-400">
              {agents.filter(a => a.model?.includes('deepseek')).length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}