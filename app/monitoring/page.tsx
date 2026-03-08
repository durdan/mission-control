'use client';

import { useEffect, useState } from 'react';

interface Agent {
  id: string;
  name: string;
  tasksCompleted: number;
  cost: number;
}

export default function MonitoringPage() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetch('/api/agents')
      .then(res => res.json())
      .then(data => setAgents(data.agents));
  }, []);

  const totalCost = agents.reduce((sum, a) => sum + a.cost, 0);
  const totalTasks = agents.reduce((sum, a) => sum + a.tasksCompleted, 0);

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Monitoring</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">System Health</h3>
          <div className="flex items-center gap-3">
            <div className="text-4xl">🟢</div>
            <div>
              <div className="text-2xl font-bold">All Systems Operational</div>
              <div className="text-sm text-gray-400">Last checked: {new Date().toLocaleString()}</div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Usage Today</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Total Tasks</span>
              <span className="font-bold">{totalTasks}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Total Cost</span>
              <span className="font-bold">${totalCost.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Cost/Task</span>
              <span className="font-bold">
                ${totalTasks > 0 ? (totalCost / totalTasks).toFixed(2) : '0.00'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="p-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold">Agent Performance</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-750">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Agent</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Tasks</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Avg Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {agents.map(agent => (
                <tr key={agent.id} className="hover:bg-gray-750 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap font-medium">{agent.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{agent.tasksCompleted}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-400">
                    {agent.tasksCompleted > 0 ? '~24 min' : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">${agent.cost.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
