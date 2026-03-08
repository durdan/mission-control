'use client';

import { useEffect, useState } from 'react';
import { FiActivity, FiCpu, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

interface AgentStatus {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'busy' | 'error';
  cpu: number;
  memory: number;
  lastHeartbeat: Date;
  currentTask?: string;
  uptime: string;
}

export default function AgentMonitor() {
  const [agents, setAgents] = useState<AgentStatus[]>([
    // Mock data - replace with real WebSocket connection
    { id: 'ceo', name: 'CEO Atlas', status: 'active', cpu: 12, memory: 45, lastHeartbeat: new Date(), uptime: '2d 14h' },
    { id: 'eng', name: 'Engineering Atlas', status: 'busy', cpu: 67, memory: 78, lastHeartbeat: new Date(), currentTask: 'Building feature X', uptime: '2d 14h' },
    { id: 'growth', name: 'Growth Atlas', status: 'active', cpu: 34, memory: 56, lastHeartbeat: new Date(), uptime: '2d 13h' },
    { id: 'product', name: 'Product Atlas', status: 'idle', cpu: 5, memory: 23, lastHeartbeat: new Date(), uptime: '2d 14h' },
    { id: 'ops', name: 'Ops Atlas', status: 'active', cpu: 89, memory: 92, lastHeartbeat: new Date(), currentTask: 'Monitoring systems', uptime: '2d 14h' },
  ]);

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => ({
        ...agent,
        cpu: Math.min(100, Math.max(0, agent.cpu + (Math.random() - 0.5) * 20)),
        memory: Math.min(100, Math.max(0, agent.memory + (Math.random() - 0.5) * 10)),
        lastHeartbeat: new Date()
      })));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <FiCheckCircle className="w-5 h-5 status-active" />;
      case 'busy': return <FiActivity className="w-5 h-5 status-busy animate-pulse" />;
      case 'error': return <FiAlertCircle className="w-5 h-5 status-error" />;
      default: return <FiCpu className="w-5 h-5 status-idle" />;
    }
  };

  const getResourceColor = (value: number) => {
    if (value > 80) return 'text-red-400';
    if (value > 60) return 'text-yellow-400';
    return 'text-green-400';
  };

  return (
    <div className="bg-primary p-8">
      <h1 className="text-3xl font-bold mb-8 text-primary">Real-Time Agent Monitoring</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.map(agent => (
          <div key={agent.id} className="card rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(agent.status)}
                <div>
                  <h3 className="font-bold text-primary">{agent.name}</h3>
                  <p className="text-xs text-tertiary">Uptime: {agent.uptime}</p>
                </div>
              </div>
              <span className={`text-xs px-2 py-1 rounded ${
                agent.status === 'active' ? 'bg-green-900 text-green-300' :
                agent.status === 'busy' ? 'bg-yellow-900 text-yellow-300' :
                agent.status === 'error' ? 'bg-red-900 text-red-300' :
                'bg-gray-700 text-gray-300'
              }`}>
                {agent.status.toUpperCase()}
              </span>
            </div>

            {agent.currentTask && (
              <div className="mb-4 p-3 bg-tertiary rounded">
                <p className="text-xs text-tertiary mb-1">Current Task:</p>
                <p className="text-sm text-secondary">{agent.currentTask}</p>
              </div>
            )}

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-tertiary">CPU</span>
                  <span className={getResourceColor(agent.cpu)}>{agent.cpu.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      agent.cpu > 80 ? 'bg-red-500' :
                      agent.cpu > 60 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${agent.cpu}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-tertiary">Memory</span>
                  <span className={getResourceColor(agent.memory)}>{agent.memory.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      agent.memory > 80 ? 'bg-red-500' :
                      agent.memory > 60 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${agent.memory}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-700">
              <p className="text-xs text-tertiary">
                Last heartbeat: {agent.lastHeartbeat.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 card rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-primary">System Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <p className="text-tertiary text-sm mb-1">Active Agents</p>
            <p className="text-2xl font-bold status-active">{agents.filter(a => a.status === 'active').length}</p>
          </div>
          <div>
            <p className="text-tertiary text-sm mb-1">Busy Agents</p>
            <p className="text-2xl font-bold status-busy">{agents.filter(a => a.status === 'busy').length}</p>
          </div>
          <div>
            <p className="text-tertiary text-sm mb-1">Avg CPU</p>
            <p className="text-2xl font-bold text-primary">
              {(agents.reduce((sum, a) => sum + a.cpu, 0) / agents.length).toFixed(0)}%
            </p>
          </div>
          <div>
            <p className="text-tertiary text-sm mb-1">Avg Memory</p>
            <p className="text-2xl font-bold text-primary">
              {(agents.reduce((sum, a) => sum + a.memory, 0) / agents.length).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}