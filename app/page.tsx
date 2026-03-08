'use client';

import { useEffect, useState } from 'react';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'idle' | 'busy' | 'error';
  currentTask: string | null;
  tasksCompleted: number;
  cost: number;
}

interface Project {
  id: string;
  name: string;
  status: string;
  progress: number;
  tasksOpen: number;
  tasksDone: number;
}

interface Activity {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  type: string;
}

export default function Home() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);

  useEffect(() => {
    fetch('/api/agents')
      .then(res => res.json())
      .then(data => setAgents(data.agents));

    fetch('/api/projects')
      .then(res => res.json())
      .then(data => setProjects(data.projects));

    fetch('/api/activity')
      .then(res => res.json())
      .then(data => setActivities(data.activities));
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalTasks = projects.reduce((sum, p) => sum + p.tasksOpen, 0);
  const totalCost = agents.reduce((sum, a) => sum + a.cost, 0);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'busy': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
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
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Overview Dashboard</h1>

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Agents</div>
            <div className="text-3xl font-bold">{activeAgents}/{agents.length} Active</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Projects</div>
            <div className="text-3xl font-bold">{projects.length} Active</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Tasks</div>
            <div className="text-3xl font-bold">{totalTasks} Open</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-2">Cost</div>
            <div className="text-3xl font-bold">${totalCost.toFixed(2)}</div>
          </div>
        </div>

        {/* Agent Grid */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">Agent Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {agents.map(agent => (
              <div key={agent.id} className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-semibold">{agent.name}</div>
                    <div className="text-sm text-gray-400">{agent.role}</div>
                  </div>
                  <span className="text-2xl">{getStatusEmoji(agent.status)}</span>
                </div>
                <div className="text-sm text-gray-300 mt-2">
                  {agent.currentTask || 'Idle'}
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-3">
                  <span>{agent.tasksCompleted} tasks</span>
                  <span>${agent.cost.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Feed */}
        <div>
          <h2 className="text-2xl font-bold mb-4">Recent Activity</h2>
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            {activities.map(activity => (
              <div key={activity.id} className="p-4 border-b border-gray-700 last:border-b-0 hover:bg-gray-750 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="text-sm text-gray-400">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="font-semibold text-blue-400">{activity.agent}</div>
                  <div className="text-gray-300">{activity.action}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
    </div>
  );
}
