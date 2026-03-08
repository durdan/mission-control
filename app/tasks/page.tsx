'use client';

import { useEffect, useState } from 'react';

interface Task {
  id: string;
  title: string;
  status: 'todo' | 'doing' | 'review' | 'done' | 'blocked';
  priority: 'low' | 'medium' | 'high';
  assignedTo: string | null;
  project: string;
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    fetch('/api/tasks')
      .then(res => res.json())
      .then(data => setTasks(data.tasks));
  }, []);

  const columns = [
    { id: 'todo', title: '📥 To Do', color: 'border-gray-600' },
    { id: 'doing', title: '🚧 Doing', color: 'border-blue-600' },
    { id: 'review', title: '👀 Review', color: 'border-yellow-600' },
    { id: 'done', title: '✅ Done', color: 'border-green-600' },
    { id: 'blocked', title: '🚫 Blocked', color: 'border-red-600' },
  ];

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getTasksByStatus = (status: string) => {
    return tasks.filter(task => task.status === status);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Tasks</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {columns.map(column => (
          <div key={column.id} className="bg-gray-800 rounded-lg p-4 border-t-4 ${column.color}">
            <h3 className="font-semibold mb-4 flex items-center justify-between">
              <span>{column.title}</span>
              <span className="text-sm text-gray-400">
                {getTasksByStatus(column.id).length}
              </span>
            </h3>

            <div className="space-y-3">
              {getTasksByStatus(column.id).map(task => (
                <div
                  key={task.id}
                  className="bg-gray-700 rounded-lg p-3 border border-gray-600 hover:border-gray-500 transition-colors cursor-pointer"
                >
                  <div className="font-medium mb-2">{task.title}</div>
                  
                  <div className="flex items-center justify-between text-xs">
                    <span className={`font-semibold ${getPriorityColor(task.priority)}`}>
                      {task.priority.toUpperCase()}
                    </span>
                    <span className="text-gray-400">{task.assignedTo || 'Unassigned'}</span>
                  </div>

                  <div className="text-xs text-gray-500 mt-2">
                    {task.project}
                  </div>
                </div>
              ))}
            </div>

            {getTasksByStatus(column.id).length === 0 && (
              <div className="text-center text-gray-500 text-sm py-8">
                No tasks
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
