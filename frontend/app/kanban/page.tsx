'use client';

import React, { useState } from 'react';
import { useOpenClaw } from '@/hooks/useOpenClaw';
import { FiPlus, FiClock, FiCheckCircle, FiAlertCircle, FiUser, FiTarget, FiActivity, FiCopy } from 'react-icons/fi';

interface Task {
  id: string;
  description: string;
  priority?: 'P0' | 'P1' | 'P2' | 'P3';
  status: 'pending' | 'assigned' | 'in_progress' | 'review' | 'completed' | 'blocked';
  agent?: string;
  created_at?: string;
}

interface Column {
  id: string;
  title: string;
  status: string[];
  color: string;
  icon: React.ReactNode;
}

const columns: Column[] = [
  { id: 'backlog', title: 'Backlog', status: ['pending'], color: 'bg-gray-500', icon: <FiClock /> },
  { id: 'assigned', title: 'Assigned', status: ['assigned'], color: 'bg-blue-500', icon: <FiUser /> },
  { id: 'progress', title: 'In Progress', status: ['in_progress'], color: 'bg-yellow-500', icon: <FiActivity /> },
  { id: 'review', title: 'Review', status: ['review'], color: 'bg-purple-500', icon: <FiTarget /> },
  { id: 'completed', title: 'Completed', status: ['completed'], color: 'bg-green-500', icon: <FiCheckCircle /> },
  { id: 'blocked', title: 'Blocked', status: ['blocked'], color: 'bg-red-500', icon: <FiAlertCircle /> }
];

const priorityColors = {
  P0: 'bg-red-600 text-white',
  P1: 'bg-orange-500 text-white',
  P2: 'bg-blue-500 text-white',
  P3: 'bg-gray-500 text-white'
};

const departmentColors = {
  engineering: 'border-blue-400',
  growth: 'border-green-400',
  product: 'border-purple-400',
  ops: 'border-orange-400',
  leadership: 'border-yellow-400',
  general: 'border-gray-400'
};

export default function KanbanPage() {
  const { tasks, agents, getTaskCommand, connected } = useOpenClaw();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTask, setNewTask] = useState({ 
    description: '', 
    priority: 'P2',
    agent: 'ceo-atlas'
  });
  const [selectedDepartment, setSelectedDepartment] = useState('all');
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  // Group tasks by status
  const tasksByColumn = columns.reduce((acc, column) => {
    acc[column.id] = tasks.filter(task => 
      column.status.includes(task.status) &&
      (selectedDepartment === 'all' || getDepartment(task) === selectedDepartment)
    );
    return acc;
  }, {} as Record<string, Task[]>);

  function getDepartment(task: Task): string {
    const agentId = task.agent?.toLowerCase() || '';
    
    // Check agent ID for department keywords
    if (agentId.includes('engineering') || agentId.includes('forge') || 
        agentId.includes('tess') || agentId.includes('arc') || 
        agentId.includes('guardian') || agentId.includes('shield') || 
        agentId.includes('docsmith')) {
      return 'engineering';
    }
    if (agentId.includes('growth') || agentId.includes('marketing') || 
        agentId.includes('social') || agentId.includes('news')) {
      return 'growth';
    }
    if (agentId.includes('product') || agentId.includes('ux') || 
        agentId.includes('design')) {
      return 'product';
    }
    if (agentId.includes('ops') || agentId.includes('sentinel') || 
        agentId.includes('monitor')) {
      return 'ops';
    }
    if (agentId.includes('ceo') || agentId.includes('atlas')) {
      return 'leadership';
    }
    return 'general';
  }

  function getAgentName(agentId?: string): string {
    if (!agentId) return 'Unassigned';
    const agent = agents.find(a => a.id === agentId);
    return agent?.name || agentId;
  }

  function handleCreateTask() {
    if (!newTask.description) return;
    
    // Generate OpenClaw command
    const command = getTaskCommand(newTask.description, newTask.agent);
    
    // Copy to clipboard
    navigator.clipboard.writeText(command).then(() => {
      setCopiedCommand(command);
      setTimeout(() => setCopiedCommand(null), 5000);
      setNewTask({ description: '', priority: 'P2', agent: 'ceo-atlas' });
      setShowCreateModal(false);
    });
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Command Notification */}
      {copiedCommand && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white p-4 rounded-lg shadow-lg max-w-md">
          <div className="flex items-center gap-2 mb-2">
            <FiCopy className="text-xl" />
            <span className="font-semibold">Command copied to clipboard!</span>
          </div>
          <code className="text-xs bg-black/30 p-2 rounded block break-all">
            {copiedCommand}
          </code>
          <p className="text-xs mt-2 opacity-90">
            Run this command in your terminal to create the task.
          </p>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Mission Control Kanban</h1>
            <p className="text-gray-400">Read-only view of OpenClaw tasks • Use CLI commands to manage tasks</p>
          </div>
          <div className="flex gap-4 items-center">
            <div className={`px-3 py-1 rounded-full text-sm ${connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {connected ? '● Connected to OpenClaw' : '● Disconnected'}
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg flex items-center gap-2"
            >
              <FiPlus /> Generate Task Command
            </button>
          </div>
        </div>

        {/* Department Filter */}
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedDepartment('all')}
            className={`px-4 py-2 rounded-lg ${selectedDepartment === 'all' ? 'bg-gray-700' : 'bg-gray-800'}`}
          >
            All Departments
          </button>
          {['engineering', 'growth', 'product', 'ops', 'leadership'].map(dept => (
            <button
              key={dept}
              onClick={() => setSelectedDepartment(dept)}
              className={`px-4 py-2 rounded-lg capitalize ${selectedDepartment === dept ? 'bg-gray-700' : 'bg-gray-800'}`}
            >
              {dept}
            </button>
          ))}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-6 gap-4">
        {columns.map(column => (
          <div key={column.id} className="bg-gray-800 rounded-lg overflow-hidden">
            <div className={`${column.color} p-3 flex items-center gap-2`}>
              {column.icon}
              <h3 className="font-semibold">{column.title}</h3>
              <span className="ml-auto bg-white/20 px-2 py-0.5 rounded-full text-sm">
                {tasksByColumn[column.id]?.length || 0}
              </span>
            </div>
            
            <div className="p-3 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {tasksByColumn[column.id]?.map(task => (
                <div
                  key={task.id}
                  className={`bg-gray-700 p-3 rounded-lg border-l-4 ${departmentColors[getDepartment(task)]}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${priorityColors[task.priority || 'P2']}`}>
                      {task.priority || 'P2'}
                    </span>
                    <span className="text-xs text-gray-400">
                      {task.id.split('_')[1]?.substring(0, 6)}
                    </span>
                  </div>
                  
                  <p className="text-sm mb-2 line-clamp-3">{task.description}</p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <FiUser />
                      {getAgentName(task.agent)}
                    </span>
                    <span className="capitalize text-xs px-2 py-0.5 rounded bg-gray-800">
                      {getDepartment(task)}
                    </span>
                  </div>
                </div>
              ))}
              
              {tasksByColumn[column.id]?.length === 0 && (
                <div className="text-gray-500 text-center py-8 text-sm">
                  No tasks
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">Generate Task Command</h2>
            <p className="text-sm text-gray-400 mb-4">
              Fill in the details below to generate an OpenClaw CLI command
            </p>
            
            <textarea
              value={newTask.description}
              onChange={(e) => setNewTask({...newTask, description: e.target.value})}
              placeholder="Describe the task..."
              className="w-full p-3 bg-gray-700 rounded-lg mb-4 h-32 resize-none"
              autoFocus
            />
            
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">Assign to Agent</label>
              <select
                value={newTask.agent}
                onChange={(e) => setNewTask({...newTask, agent: e.target.value})}
                className="w-full p-3 bg-gray-700 rounded-lg"
              >
                <optgroup label="Orchestrators">
                  <option value="ceo-atlas">CEO Atlas (Global Orchestrator)</option>
                  <option value="engineering-atlas">Engineering Atlas</option>
                  <option value="growth-atlas">Growth Atlas</option>
                  <option value="product-atlas">Product Atlas</option>
                  <option value="ops-atlas">Ops Atlas</option>
                </optgroup>
                <optgroup label="Engineering Specialists">
                  <option value="forge">Forge (Code Generation)</option>
                  <option value="tess">Tess (Testing)</option>
                  <option value="arc">Arc (Architecture)</option>
                  <option value="guardian">Guardian (Code Review)</option>
                  <option value="shield">Shield (Security)</option>
                  <option value="docsmith">DocSmith (Documentation)</option>
                </optgroup>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">Priority</label>
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask({...newTask, priority: e.target.value})}
                className="w-full p-3 bg-gray-700 rounded-lg"
              >
                <option value="P0">P0 - Critical</option>
                <option value="P1">P1 - High</option>
                <option value="P2">P2 - Medium</option>
                <option value="P3">P3 - Low</option>
              </select>
            </div>
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTask}
                disabled={!newTask.description}
                className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <FiCopy /> Copy Command
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}