'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ClusterDashboard } from "@/components/v3/ClusterDashboard";
import { MetricsDashboard } from "@/components/v3/MetricsDashboard";
import { ResourcesDashboard } from "@/components/v3/ResourcesDashboard";
import { WorkflowsDashboard } from "@/components/v3/WorkflowsDashboard";
import DemoModeToggle from "@/components/DemoModeToggle";

export default function V3Dashboard() {
  return (
    <div className="container mx-auto p-6">
      <DemoModeToggle />
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Mission Control V3</h1>
        <p className="text-gray-600">Enterprise features for OpenClaw management</p>
      </div>

      <Tabs defaultValue="clusters" className="space-y-4">
        <TabsList>
          <TabsTrigger value="clusters">Clusters</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
        </TabsList>

        <TabsContent value="clusters">
          <ClusterDashboard />
        </TabsContent>

        <TabsContent value="metrics">
          <MetricsDashboard />
        </TabsContent>

        <TabsContent value="resources">
          <ResourcesDashboard />
        </TabsContent>

        <TabsContent value="workflows">
          <WorkflowsDashboard />
        </TabsContent>
      </Tabs>
    </div>
  );
}