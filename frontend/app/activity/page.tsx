'use client';

import { useEffect, useState } from 'react';

interface Activity {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  type: string;
}

export default function ActivityPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetch('/api/activity')
      .then(res => res.json())
      .then(data => setActivities(data.activities));
  }, []);

  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(a => a.type === filter);

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'task-start': return 'bg-blue-500';
      case 'task-complete': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'system': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Activity Log</h1>
        
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === 'all' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('task-start')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === 'task-start' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            Tasks
          </button>
          <button
            onClick={() => setFilter('system')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === 'system' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            System
          </button>
          <button
            onClick={() => setFilter('error')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === 'error' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            Errors
          </button>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="divide-y divide-gray-700">
          {filteredActivities.length > 0 ? (
            filteredActivities.map(activity => (
              <div key={activity.id} className="p-4 hover:bg-gray-750 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <span className={`inline-block w-3 h-3 rounded-full ${getTypeColor(activity.type)}`} />
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-sm text-gray-400">
                        {new Date(activity.timestamp).toLocaleString()}
                      </span>
                      <span className="font-semibold text-blue-400">{activity.agent}</span>
                    </div>
                    <div className="text-gray-300">{activity.action}</div>
                  </div>

                  <div className="flex-shrink-0">
                    <span className="px-2 py-1 text-xs rounded bg-gray-700 text-gray-400">
                      {activity.type.replace('-', ' ')}
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">
              No activities found
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
          Export Activity Log
        </button>
      </div>
    </div>
  );
}
