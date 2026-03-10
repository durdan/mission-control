// Hook for connecting to the OpenClaw Bridge API
import { useEffect, useState } from 'react';

const BRIDGE_API = 'http://localhost:3001';
const WS_URL = 'ws://localhost:3002';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'idle' | 'busy' | 'inactive';
  type: 'specialist' | 'orchestrator' | 'global-orchestrator' | 'domain-orchestrator';
  domain?: string;
  orchestrator?: string;
  tasksCompleted: number;
  cost: number;
  currentTask?: string;
}

interface Task {
  id: string;
  description: string;
  priority: string;
  status: string;
  routing: {
    orchestrator: string;
    agent: string;
  };
  createdAt: string;
}

interface Activity {
  id: string;
  timestamp: string;
  agent_id: string;
  action: string;
}

export function useAgentData() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [hierarchy, setHierarchy] = useState<any>(null);
  const [connected, setConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  // Fetch initial data
  useEffect(() => {
    fetchAgents();
    fetchTasks();
    fetchActivities();
    fetchHierarchy();
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const websocket = new WebSocket(WS_URL);
    
    websocket.onopen = () => {
      console.log('✅ Connected to OpenClaw Bridge WebSocket');
      setConnected(true);
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    websocket.onclose = () => {
      console.log('❌ Disconnected from OpenClaw Bridge');
      setConnected(false);
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/agents`);
      const data = await response.json();
      setAgents(data.agents);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/tasks`);
      const data = await response.json();
      setTasks(data.tasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const fetchActivities = async () => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/activity`);
      const data = await response.json();
      setActivities(data.activities);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    }
  };

  const fetchHierarchy = async () => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/hierarchy`);
      const data = await response.json();
      setHierarchy(data.hierarchy);
    } catch (error) {
      console.error('Failed to fetch hierarchy:', error);
    }
  };

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'connected':
        console.log('✅ WebSocket connected to OpenClaw Bridge');
        break;
        
      case 'update':
        // Handle real-time session updates from OpenClaw bridge
        if (data.data && data.data.sessions) {
          const updatedAgents = data.data.sessions.map((session: any) => ({
            id: session.id,
            name: session.key.split(':').pop() || session.key,
            role: session.kind,
            status: 'active',
            type: session.kind === 'direct' ? 'specialist' : 'orchestrator',
            model: session.model,
            session: session,
            tasksCompleted: 0,
            cost: 0
          }));
          setAgents(updatedAgents);
          console.log('📊 Updated agents from sessions:', updatedAgents);
        }
        break;
        
      case 'initial':
        if (data.agents) setAgents(data.agents);
        if (data.taskQueue) setTasks(data.taskQueue);
        break;
        
      case 'agent_update':
        setAgents(prev => 
          prev.map(a => a.id === data.agent.id ? data.agent : a)
        );
        break;
        
      case 'task_created':
        setTasks(prev => [data.task, ...prev]);
        break;
        
      case 'activity':
        setActivities(prev => [data.activity, ...prev.slice(0, 99)]);
        break;
        
      case 'inter_agent_message':
        console.log('Inter-agent message:', data.message);
        break;
        
      case 'heartbeat':
        // Keep connection alive
        break;
    }
  };

  const createTask = async (description: string, priority: string = 'P2') => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, priority })
      });
      const data = await response.json();
      return data.task;
    } catch (error) {
      console.error('Failed to create task:', error);
      throw error;
    }
  };

  const sendMessage = async (from: string, to: string, message: string) => {
    try {
      const response = await fetch(`${BRIDGE_API}/api/comms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from, to, message })
      });
      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  };

  return {
    agents,
    tasks,
    activities,
    hierarchy,
    connected,
    createTask,
    sendMessage,
    refetch: {
      agents: fetchAgents,
      tasks: fetchTasks,
      activities: fetchActivities,
      hierarchy: fetchHierarchy
    }
  };
}