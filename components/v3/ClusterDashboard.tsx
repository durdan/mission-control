"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Server, 
  Activity, 
  AlertCircle, 
  CheckCircle,
  Globe,
  Cpu,
  HardDrive,
  Network
} from 'lucide-react';

interface Cluster {
  cluster_id: string;
  name: string;
  gateway_url: string;
  region: string;
  status: string;
  current_agents: number;
  max_agents: number;
  utilization: number;
  last_heartbeat: string;
}

export function ClusterDashboard() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchClusters();
    const interval = setInterval(fetchClusters, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchClusters = async () => {
    try {
      // Check if we're in demo mode
      const isDemoMode = localStorage.getItem('demoMode') !== 'false';
      const response = await fetch(`http://localhost:8001/api/v3/clusters?demo=${isDemoMode}`);
      if (!response.ok) throw new Error('Failed to fetch clusters');
      const data = await response.json();
      setClusters(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clusters');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'offline':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'offline':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization < 50) return 'bg-green-500';
    if (utilization < 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const handleDrainCluster = async (clusterId: string) => {
    try {
      const response = await fetch(`http://localhost:8001/api/v3/clusters/${clusterId}/drain`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to drain cluster');
      await fetchClusters();
    } catch (err) {
      console.error('Error draining cluster:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading clusters...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Server className="h-6 w-6" />
          Cluster Management
        </h2>
        <Button 
          onClick={fetchClusters}
          variant="outline"
          className="flex items-center gap-2"
        >
          <Activity className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {clusters.map((cluster) => (
          <Card key={cluster.cluster_id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-lg">{cluster.name}</CardTitle>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Globe className="h-3 w-3" />
                    {cluster.region}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(cluster.status)}
                  <Badge className={getStatusColor(cluster.status)}>
                    {cluster.status}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Agent Capacity */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Agent Capacity</span>
                  <span className="font-medium">
                    {cluster.current_agents} / {cluster.max_agents}
                  </span>
                </div>
                <Progress 
                  value={cluster.utilization} 
                  className="h-2"
                  indicatorClassName={getUtilizationColor(cluster.utilization)}
                />
              </div>

              {/* Gateway URL */}
              <div className="text-sm">
                <div className="text-gray-600 mb-1">Gateway</div>
                <div className="font-mono text-xs bg-gray-100 p-2 rounded truncate">
                  {cluster.gateway_url}
                </div>
              </div>

              {/* Last Heartbeat */}
              {cluster.last_heartbeat && (
                <div className="text-sm text-gray-500">
                  Last heartbeat: {new Date(cluster.last_heartbeat).toLocaleString()}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button 
                  size="sm" 
                  variant="outline"
                  className="flex-1"
                  onClick={() => window.open(`/clusters/${cluster.cluster_id}`, '_blank')}
                >
                  Details
                </Button>
                {cluster.status === 'online' && (
                  <Button 
                    size="sm" 
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleDrainCluster(cluster.cluster_id)}
                  >
                    Drain
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {clusters.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No clusters registered. Start by registering a cluster.
        </div>
      )}

      {/* Cluster Statistics */}
      {clusters.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Cluster Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">{clusters.length}</div>
                <div className="text-sm text-gray-500">Total Clusters</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {clusters.filter(c => c.status === 'online').length}
                </div>
                <div className="text-sm text-gray-500">Online</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {clusters.reduce((acc, c) => acc + c.current_agents, 0)}
                </div>
                <div className="text-sm text-gray-500">Total Agents</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {Math.round(
                    clusters.reduce((acc, c) => acc + c.utilization, 0) / clusters.length
                  )}%
                </div>
                <div className="text-sm text-gray-500">Avg Utilization</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}