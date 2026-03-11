'use client';

import { useAgentData } from '@/hooks/useAgentData';
import { useState } from 'react';
import { FiSend, FiPlus, FiActivity, FiCpu, FiKey, FiSettings } from 'react-icons/fi';
import EnrollmentModal from '@/components/EnrollmentModal';
import DemoModeToggle from '@/components/DemoModeToggle';

export default function Home() {
  const { agents, tasks, activities, hierarchy, connected, createTask } = useAgentData();
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [showEnrollmentModal, setShowEnrollmentModal] = useState(false);
  const [taskDescription, setTaskDescription] = useState('');
  const [taskPriority, setTaskPriority] = useState('P2');

  const orchestrators = agents.filter(a => a.type?.includes('orchestrator'));
  const specialists = agents.filter(a => a.type === 'specialist');
  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalTasks = tasks.length;
  const totalCost = agents.reduce((sum, a) => sum + (a.cost || 0), 0);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'status-active';
      case 'busy': return 'status-busy';
      case 'inactive': return 'text-gray-500';
      default: return 'status-idle';
    }
  };

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case 'active': return '🟢';
      case 'busy': return '🟡';
      case 'inactive': return '⚫';
      default: return '⚪';
    }
  };

  const handleCreateTask = async () => {
    if (!taskDescription) return;
    
    try {
      await createTask(taskDescription, taskPriority);
      setTaskDescription('');
      setShowTaskModal(false);
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleEnroll = async (token: string) => {
    const response = await fetch('http://localhost:3001/api/enroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Enrollment failed');
    }
    
    // Reconnect after successful enrollment
    window.location.reload();
  };

  return (
    <div className="p-8 bg-primary">
      <DemoModeToggle />
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">Mission Control</h1>
        <div className="flex items-center gap-4">
          <nav className="flex gap-2">
            <a href="/" className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white">Dashboard</a>
            <a href="/kanban" className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white">Kanban</a>
            <a href="/hierarchy" className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white">Hierarchy</a>
          </nav>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${connected ? 'bg-green-900' : 'bg-red-900'}`}>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
            <span className="text-xs text-secondary">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <button
            onClick={() => setShowEnrollmentModal(true)}
            className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded-lg flex items-center gap-2"
            title="Configure OpenClaw Gateway Token"
          >
            <FiKey className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowTaskModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <FiPlus /> New Task
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
        <div className="card card-hover rounded-lg p-6">
          <div className="text-tertiary text-sm mb-2">Sessions</div>
          <div className="text-3xl font-bold text-primary">{agents.length}</div>
        </div>
        <div className="card card-hover rounded-lg p-6">
          <div className="text-tertiary text-sm mb-2">Active Agents</div>
          <div className="text-3xl font-bold status-active">{activeAgents}</div>
        </div>
        <div className="card card-hover rounded-lg p-6">
          <div className="text-tertiary text-sm mb-2">Tasks</div>
          <div className="text-3xl font-bold text-primary">{totalTasks}</div>
        </div>
        <div className="card card-hover rounded-lg p-6">
          <div className="text-tertiary text-sm mb-2">Models</div>
          <div className="text-3xl font-bold text-primary">{new Set(agents.map(a => a.model?.split('/')[0])).size}</div>
        </div>
        <div className="card card-hover rounded-lg p-6">
          <div className="text-tertiary text-sm mb-2">Cost</div>
          <div className="text-3xl font-bold text-primary">${totalCost.toFixed(2)}</div>
        </div>
      </div>

      {/* Active Sessions Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-primary">Active Sessions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map(agent => (
            <div key={agent.id} className="card rounded-lg p-6 border-l-4 border-green-500">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="text-lg font-bold text-primary">{agent.name || 'Agent'}</h3>
                  <p className="text-sm text-secondary">Session: {agent.id?.slice(0, 8)}...</p>
                </div>
                <span className="px-2 py-1 bg-green-900 text-green-300 text-xs rounded-full">
                  {agent.status}
                </span>
              </div>
              
              {agent.model && (
                <div className="mb-3">
                  <span className="text-xs text-tertiary">Model:</span>
                  <span className="text-sm text-primary ml-2">{agent.model}</span>
                </div>
              )}
              
              {agent.session && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-tertiary">Type:</span>
                    <span className="text-primary">{agent.session.kind}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-tertiary">Key:</span>
                    <span className="text-primary font-mono text-xs">{agent.session.key}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-tertiary">Age:</span>
                    <span className="text-primary">{agent.session.age}</span>
                  </div>
                  {agent.session.raw && agent.session.raw.includes('k/') && (
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <div className="text-xs text-tertiary mb-1">Token Usage:</div>
                      <div className="text-sm font-mono text-primary">
                        {agent.session.raw.match(/\d+k\/\d+k \(\d+%\)/)?.[0] || 'N/A'}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {agents.length === 0 && (
            <div className="col-span-2 text-center py-8 text-tertiary">
              No active sessions. Run `openclaw task "your task"` to start an agent.
            </div>
          )}
        </div>
      </div>

      {/* Orchestrators Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-primary">Orchestrators</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {orchestrators.map(agent => (
            <div key={agent.id} className="card card-hover rounded-lg p-4 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <FiCpu className={`w-4 h-4 ${getStatusColor(agent.status)}`} />
                    <div className="font-semibold text-primary">{agent.name}</div>
                  </div>
                  <div className="text-sm text-secondary">{agent.role}</div>
                </div>
                <span className="text-xl">{getStatusEmoji(agent.status)}</span>
              </div>
              {agent.type === 'domain-orchestrator' && (
                <div className="text-xs text-tertiary mt-2">
                  Manages {agent.children?.length || 0} agents
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Specialists by Domain */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-primary">Specialist Agents</h2>
        
        {/* Engineering Team */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3 text-secondary">Engineering Team</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {specialists.filter(a => a.domain === 'engineering').map(agent => (
              <div key={agent.id} className="card rounded-lg p-3">
                <div className="font-medium text-primary">{agent.name}</div>
                <div className="text-xs text-secondary">{agent.role}</div>
                <div className="flex items-center gap-1 mt-2">
                  <span className={`text-xs ${getStatusColor(agent.status)}`}>{agent.status}</span>
                  {getStatusEmoji(agent.status)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Growth Team */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3 text-secondary">Growth Team</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {specialists.filter(a => a.domain === 'growth').map(agent => (
              <div key={agent.id} className="card rounded-lg p-3">
                <div className="font-medium text-primary">{agent.name || agent.id}</div>
                <div className="text-xs text-secondary">{agent.role || 'Specialist'}</div>
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-xs ${getStatusColor(agent.status)}`}>{agent.status}</span>
                  <span className="text-xs text-tertiary">{agent.tasksCompleted} tasks</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-primary flex items-center gap-2">
          <FiActivity /> Recent Activity
        </h2>
        <div className="card rounded-lg max-h-64 overflow-y-auto">
          {activities.length > 0 ? (
            activities.map(activity => (
              <div key={activity.id} className="p-3 border-b border-gray-700 last:border-b-0 hover:bg-tertiary transition-colors">
                <div className="flex items-center gap-3">
                  <div className="text-xs text-tertiary">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="text-sm font-medium text-blue-400">{activity.agent_id}</div>
                  <div className="text-sm text-secondary">{activity.action}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-tertiary">
              No recent activity. Create a task to get started!
            </div>
          )}
        </div>
      </div>

      {/* Task Creation Modal */}
      {showTaskModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-secondary rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4 text-primary">Create New Task</h3>
            
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="Describe the task..."
              className="w-full p-3 bg-tertiary text-primary rounded-lg mb-4 h-32 resize-none"
            />
            
            <div className="mb-4">
              <label className="text-sm text-secondary mb-2 block">Priority</label>
              <select
                value={taskPriority}
                onChange={(e) => setTaskPriority(e.target.value)}
                className="w-full p-2 bg-tertiary text-primary rounded-lg"
              >
                <option value="P0">P0 - Critical</option>
                <option value="P1">P1 - High</option>
                <option value="P2">P2 - Medium</option>
                <option value="P3">P3 - Low</option>
              </select>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={handleCreateTask}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg flex items-center justify-center gap-2"
              >
                <FiSend /> Create Task
              </button>
              <button
                onClick={() => setShowTaskModal(false)}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-2 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Enrollment Modal */}
      <EnrollmentModal
        isOpen={showEnrollmentModal}
        onClose={() => setShowEnrollmentModal(false)}
        onEnroll={handleEnroll}
        currentStatus={connected ? 'Connected to OpenClaw Gateway' : 'Not connected - Token may be invalid'}
      />
    </div>
  );
}