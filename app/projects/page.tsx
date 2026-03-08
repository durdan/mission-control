'use client';

import { useEffect, useState } from 'react';

interface Project {
  id: string;
  name: string;
  status: string;
  progress: number;
  tasksOpen: number;
  tasksDone: number;
  tasksBlocked: number;
  teamSize: number;
  nextMilestone: string;
  milestoneDue: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    fetch('/api/projects')
      .then(res => res.json())
      .then(data => setProjects(data.projects));
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in-progress': return 'bg-blue-500';
      case 'planning': return 'bg-yellow-500';
      case 'not-started': return 'bg-gray-500';
      case 'completed': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Projects</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(project => (
          <div key={project.id} className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden hover:border-gray-600 transition-colors">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-semibold mb-2">{project.name}</h3>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(project.status)} text-white`}>
                      {project.status.replace('-', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-300">Progress</span>
                  <span className="font-semibold text-white">{project.progress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${project.progress}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-yellow-400">{project.tasksOpen}</div>
                  <div className="text-xs text-gray-300 font-medium">Open</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-400">{project.tasksDone}</div>
                  <div className="text-xs text-gray-300 font-medium">Done</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-400">{project.tasksBlocked}</div>
                  <div className="text-xs text-gray-300 font-medium">Blocked</div>
                </div>
              </div>

              <div className="border-t border-gray-700 pt-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-300">Team Size</span>
                  <span className="font-semibold text-white">{project.teamSize} agents</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-300">Next Milestone</span>
                  <span className="font-semibold text-white">{project.nextMilestone}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">Due</span>
                  <span className="font-semibold text-white">{new Date(project.milestoneDue).toLocaleDateString()}</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-750 px-6 py-3 flex gap-2">
              <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors">
                View Details
              </button>
              <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">
                ⚙️
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
