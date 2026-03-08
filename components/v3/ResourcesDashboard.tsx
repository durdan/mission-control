"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Server,
  HardDrive,
  Cpu,
  MemoryStick,
  Network,
  DollarSign,
  Clock,
  Zap
} from 'lucide-react';

export function ResourcesDashboard() {
  const [quotas, setQuotas] = useState<any>(null);
  const [provisions, setProvisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResources();
    const interval = setInterval(fetchResources, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchResources = async () => {
    try {
      const [quotasRes, provisionsRes] = await Promise.all([
        fetch('http://localhost:8001/api/v3/resources/quotas'),
        fetch('http://localhost:8001/api/v3/resources/provisions')
      ]);

      if (quotasRes.ok) {
        const quotasData = await quotasRes.json();
        setQuotas(quotasData.quotas);
      }

      if (provisionsRes.ok) {
        const provisionsData = await provisionsRes.json();
        setProvisions(provisionsData);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching resources:', err);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading resources...</div>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2">
        <Server className="h-6 w-6" />
        Resource Management
      </h2>

      {/* Quota Overview */}
      {quotas && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Cpu className="h-4 w-4" />
                CPU Quota
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Used</span>
                  <span>{quotas.compute?.vcpus_used || 0} / {quotas.compute?.vcpus_total || 1000} vCPUs</span>
                </div>
                <Progress 
                  value={(quotas.compute?.vcpus_used || 0) / (quotas.compute?.vcpus_total || 1) * 100} 
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <MemoryStick className="h-4 w-4" />
                Memory Quota
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Used</span>
                  <span>{quotas.compute?.memory_gb_used || 0} / {quotas.compute?.memory_gb_total || 4000} GB</span>
                </div>
                <Progress 
                  value={(quotas.compute?.memory_gb_used || 0) / (quotas.compute?.memory_gb_total || 1) * 100} 
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <HardDrive className="h-4 w-4" />
                Storage Quota
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Used</span>
                  <span>{quotas.storage?.disk_gb_used || 0} / {quotas.storage?.disk_gb_total || 100000} GB</span>
                </div>
                <Progress 
                  value={(quotas.storage?.disk_gb_used || 0) / (quotas.storage?.disk_gb_total || 1) * 100} 
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active Provisions */}
      <Card>
        <CardHeader>
          <CardTitle>Active Provisions</CardTitle>
        </CardHeader>
        <CardContent>
          {provisions.length > 0 ? (
            <div className="space-y-3">
              {provisions.map((provision) => (
                <div key={provision.provision_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{provision.provision_id}</div>
                      <div className="text-sm text-gray-500">
                        Strategy: {provision.strategy}
                      </div>
                    </div>
                    <Badge>{provision.status}</Badge>
                  </div>
                  {provision.resources && (
                    <div className="mt-2 text-sm text-gray-600">
                      {provision.resources.compute && (
                        <div>Compute: {provision.resources.compute.vcpus} vCPUs, {provision.resources.compute.memory_gb} GB RAM</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No active resource provisions
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Provision
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Schedule
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Cost Report
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <Network className="h-4 w-4" />
              Optimize
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}