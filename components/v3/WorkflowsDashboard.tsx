"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  GitBranch, 
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Play,
  Pause,
  SkipForward
} from 'lucide-react';

export function WorkflowsDashboard() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      // Fetch active workflows from API
      const workflowsResponse = await fetch('http://localhost:8001/api/v3/workflows/active');
      if (workflowsResponse.ok) {
        const workflowsData = await workflowsResponse.json();
        setWorkflows(workflowsData.workflows || []);
      } else {
        // If API not available, show empty state
        setWorkflows([]);
      }

      // Fetch workflow templates
      const templatesResponse = await fetch('http://localhost:8001/api/v3/workflows/templates');
      if (templatesResponse.ok) {
        const templatesData = await templatesResponse.json();
        setTemplates(templatesData.templates || []);
      } else {
        // Default templates if API not available
        setTemplates([
          {
            name: 'resource-approval',
            description: 'Approval for resource provisioning',
            steps: 3
          },
          {
            name: 'deployment-approval',
            description: 'Multi-stage deployment approval',
            steps: 4
          },
          {
            name: 'emergency-change',
            description: 'Fast-track emergency changes',
            steps: 2
          }
        ]);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching workflows:', err);
      setWorkflows([]);
      setTemplates([]);
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'waiting':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'waiting':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading workflows...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2">
        <GitBranch className="h-6 w-6" />
        Workflow Management
      </h2>

      {/* Active Workflows */}
      <Card>
        <CardHeader>
          <CardTitle>Active Workflows</CardTitle>
        </CardHeader>
        <CardContent>
          {workflows.length > 0 ? (
            <div className="space-y-4">
              {workflows.map((workflow) => (
                <div key={workflow.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(workflow.status)}
                      <div>
                        <div className="font-medium">{workflow.id}</div>
                        <div className="text-sm text-gray-500">{workflow.template}</div>
                      </div>
                    </div>
                    <Badge className={getStatusColor(workflow.status)}>
                      {workflow.status}
                    </Badge>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Progress</span>
                      <span>{workflow.steps_completed} / {workflow.steps_total} steps</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full transition-all"
                        style={{ width: `${(workflow.steps_completed / workflow.steps_total) * 100}%` }}
                      />
                    </div>
                  </div>

                  {workflow.current_step && workflow.status === 'running' && (
                    <div className="mt-2 text-sm text-gray-600">
                      Current step: {workflow.current_step}
                    </div>
                  )}

                  {/* Actions */}
                  {workflow.status === 'running' && (
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline">
                        <Pause className="h-3 w-3 mr-1" />
                        Pause
                      </Button>
                      <Button size="sm" variant="outline">
                        <SkipForward className="h-3 w-3 mr-1" />
                        Skip
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No active workflows
            </div>
          )}
        </CardContent>
      </Card>

      {/* Workflow Templates */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Templates</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <div key={template.name} className="border rounded-lg p-4">
                <div className="font-medium mb-1">{template.name}</div>
                <div className="text-sm text-gray-600 mb-3">{template.description}</div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{template.steps} steps</span>
                  <Button size="sm" variant="outline">
                    <Play className="h-3 w-3 mr-1" />
                    Start
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Workflow Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total Workflows</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workflows.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {workflows.filter(w => w.status === 'running').length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {workflows.filter(w => w.status === 'completed').length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">95%</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}