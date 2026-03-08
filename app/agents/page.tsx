'use client';

import { useEffect, useState } from 'react';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'idle' | 'busy' | 'error';
  currentTask: string | null;
  lastActive: string | null;
  tasksCompleted: number;
  cost: number;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  useEffect(() => {
    fetch('/api/agents')
      .then(res => res.json())
      .then(data => {
        setAgents(data.agents);
        if (data.agents.length > 0) {
          setSelectedAgent(data.agents[0]);
        }
      });
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-500';
      case 'busy': return 'text-yellow-500';
      case 'error': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case 'active': return '🟢';
      case 'busy': return '🟡';
      case 'error': return '🔴';
      default: return '⚫';
    }
  };

  return (
    <div className="flex h-screen">
      {/* Agent List Sidebar */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Agents ({agents.length})</h2>
          <div className="space-y-2">
            {agents.map(agent => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className={`w-full text-left p-4 rounded-lg transition-colors ${
                  selectedAgent?.id === agent.id
                    ? 'bg-gray-700 border border-gray-600'
                    : 'bg-gray-750 hover:bg-gray-700 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">{agent.name}</span>
                  <span className="text-xl">{getStatusEmoji(agent.status)}</span>
                </div>
                <div className="text-sm text-gray-400">{agent.role}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Detail Panel */}
      <div className="flex-1 p-8 overflow-y-auto">
        {selectedAgent ? (
          <div>
            <div className="mb-8">
              <div className="flex items-center gap-4 mb-4">
                <span className="text-4xl">{getStatusEmoji(selectedAgent.status)}</span>
                <div>
                  <h1 className="text-3xl font-bold">{selectedAgent.name}</h1>
                  <p className="text-gray-400">{selectedAgent.role}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="text-gray-400 text-sm mb-2">Status</div>
                <div className={`text-2xl font-bold capitalize ${getStatusColor(selectedAgent.status)}`}>
                  {selectedAgent.status}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="text-gray-400 text-sm mb-2">Tasks Completed</div>
                <div className="text-2xl font-bold">{selectedAgent.tasksCompleted}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div className="text-gray-400 text-sm mb-2">Cost</div>
                <div className="text-2xl font-bold">${selectedAgent.cost.toFixed(2)}</div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
              <h3 className="text-lg font-semibold mb-4">Current Task</h3>
              <p className="text-gray-300">
                {selectedAgent.currentTask || 'No active task'}
              </p>
            </div>

            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6">
              <h3 className="text-lg font-semibold mb-4">Last Active</h3>
              <p className="text-gray-300">
                {selectedAgent.lastActive 
                  ? new Date(selectedAgent.lastActive).toLocaleString()
                  : 'Never'
                }
              </p>
            </div>

            <div className="flex gap-4">
              <button className="px-6 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg transition-colors">
                Pause Agent
              </button>
              <button className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors">
                Kill Agent
              </button>
              <button className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                Reassign Task
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select an agent to view details
          </div>
        )}
      </div>
    </div>
  );
}
