'use client';

import { useEffect, useRef } from 'react';

interface AgentNode {
  id: string;
  name: string;
  title: string;
  type: 'orchestrator' | 'agent';
  status: 'active' | 'idle' | 'busy';
  children?: AgentNode[];
}

const agentHierarchy: AgentNode = {
  id: 'ceo',
  name: 'CEO Atlas',
  title: 'Global Orchestrator',
  type: 'orchestrator',
  status: 'active',
  children: [
    {
      id: 'eng',
      name: 'Engineering Atlas',
      title: 'SDLC Orchestrator',
      type: 'orchestrator',
      status: 'active',
      children: [
        { id: 'forge', name: 'Forge', title: 'Developer', type: 'agent', status: 'busy' },
        { id: 'tess', name: 'Tess', title: 'QA/Test', type: 'agent', status: 'idle' },
        { id: 'arc', name: 'Arc', title: 'Architect', type: 'agent', status: 'active' },
        { id: 'guardian', name: 'Guardian', title: 'Security', type: 'agent', status: 'idle' },
        { id: 'shield', name: 'Shield', title: 'Gate/Review', type: 'agent', status: 'idle' },
        { id: 'docsmith', name: 'Docsmith', title: 'Docs/Release', type: 'agent', status: 'idle' }
      ]
    },
    {
      id: 'mkt',
      name: 'Growth Atlas',
      title: 'Marketing Orchestrator',
      type: 'orchestrator',
      status: 'active',
      children: [
        { id: 'orbit', name: 'Orbit', title: 'SEO', type: 'agent', status: 'active' },
        { id: 'beacon', name: 'Beacon', title: 'Copy/Content', type: 'agent', status: 'busy' },
        { id: 'pulse', name: 'Pulse', title: 'Lifecycle/CRM', type: 'agent', status: 'idle' },
        { id: 'relay', name: 'Relay', title: 'Outreach/PR', type: 'agent', status: 'idle' },
        { id: 'lumen', name: 'Lumen', title: 'Design Support', type: 'agent', status: 'idle' }
      ]
    },
    {
      id: 'prd',
      name: 'Product Atlas',
      title: 'Discovery Orchestrator',
      type: 'orchestrator',
      status: 'idle',
      children: [
        { id: 'sage', name: 'Sage', title: 'Requirements', type: 'agent', status: 'idle' },
        { id: 'nova', name: 'Nova', title: 'User Research/UX', type: 'agent', status: 'idle' },
        { id: 'signal', name: 'Signal', title: 'Analytics/Insights', type: 'agent', status: 'idle' }
      ]
    },
    {
      id: 'ops',
      name: 'Ops Atlas',
      title: 'Reliability/Compliance',
      type: 'orchestrator',
      status: 'active',
      children: [
        { id: 'sentinel', name: 'Sentinel', title: 'Monitoring/Alerts', type: 'agent', status: 'active' },
        { id: 'auditor', name: 'Auditor', title: 'ISO/Policy', type: 'agent', status: 'idle' },
        { id: 'responder', name: 'Responder', title: 'Incident Triage', type: 'agent', status: 'idle' }
      ]
    }
  ]
};

export default function HierarchyPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth - 256;
    canvas.height = window.innerHeight;

    const nodeWidth = 180;
    const nodeHeight = 60;
    const horizontalSpacing = 220;
    const verticalSpacing = 100;
    const startX = 100;
    const startY = 100;

    const getStatusColor = (status: string) => {
      switch (status) {
        case 'active': return '#10b981';
        case 'busy': return '#f59e0b';
        case 'idle': return '#6b7280';
        default: return '#6b7280';
      }
    };

    const drawNode = (node: AgentNode, x: number, y: number) => {
      // Draw box
      ctx.fillStyle = node.type === 'orchestrator' ? '#1e293b' : '#334155';
      ctx.fillRect(x, y, nodeWidth, nodeHeight);
      
      // Draw border
      ctx.strokeStyle = getStatusColor(node.status);
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, nodeWidth, nodeHeight);
      
      // Draw status indicator
      ctx.fillStyle = getStatusColor(node.status);
      ctx.beginPath();
      ctx.arc(x + nodeWidth - 15, y + 15, 5, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw text
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px sans-serif';
      ctx.fillText(node.name, x + 10, y + 25);
      
      ctx.fillStyle = '#94a3b8';
      ctx.font = '12px sans-serif';
      ctx.fillText(node.title, x + 10, y + 45);
      
      return { x: x + nodeWidth / 2, y: y + nodeHeight };
    };

    const drawConnection = (fromX: number, fromY: number, toX: number, toY: number) => {
      ctx.strokeStyle = '#475569';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(fromX, fromY);
      ctx.lineTo(toX, toY);
      ctx.stroke();
    };

    const drawHierarchy = (node: AgentNode, x: number, y: number, level: number = 0) => {
      const nodePos = drawNode(node, x, y);
      
      if (node.children && node.children.length > 0) {
        const childrenWidth = node.children.length * horizontalSpacing;
        const startChildX = x - (childrenWidth - nodeWidth) / 2;
        
        node.children.forEach((child, index) => {
          const childX = startChildX + (index * horizontalSpacing);
          const childY = y + verticalSpacing + nodeHeight;
          
          drawConnection(nodePos.x, nodePos.y, childX + nodeWidth / 2, childY);
          drawHierarchy(child, childX, childY, level + 1);
        });
      }
    };

    // Clear canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw hierarchy
    drawHierarchy(agentHierarchy, canvas.width / 2 - nodeWidth / 2, startY);

    // Add title
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 24px sans-serif';
    ctx.fillText('Agent Hierarchy', 40, 50);
    
    // Add legend
    const legendY = canvas.height - 50;
    ctx.font = '12px sans-serif';
    
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.arc(40, legendY, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.fillText('Active', 55, legendY + 5);
    
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath();
    ctx.arc(120, legendY, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.fillText('Busy', 135, legendY + 5);
    
    ctx.fillStyle = '#6b7280';
    ctx.beginPath();
    ctx.arc(190, legendY, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.fillText('Idle', 205, legendY + 5);
  }, []);

  return (
    <div className="h-screen overflow-hidden bg-gray-900">
      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  );
}