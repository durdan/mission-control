"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  Activity, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  MemoryStick,
  HardDrive,
  Network
} from 'lucide-react';

interface MetricsSummary {
  agents: {
    total: number;
    active: number;
  };
  tasks: {
    pending: number;
    success_rate: number;
  };
  resources: {
    cpu_usage: number;
    memory_usage: number;
  };
}

interface TimeSeries {
  timestamp: string;
  value: number;
}

interface Alert {
  metric: string;
  violation: string;
  value: number;
  timestamp: string;
}

export function MetricsDashboard() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeries[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('tasks.success_rate');
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [selectedMetric, timeRange]);

  const fetchMetrics = async () => {
    try {
      // Fetch summary
      const summaryResponse = await fetch('http://localhost:8001/api/v3/metrics/summary');
      if (summaryResponse.ok) {
        const summaryData = await summaryResponse.json();
        setSummary(summaryData);
      }

      // Fetch time series
      const tsResponse = await fetch('http://localhost:8001/api/v3/metrics/timeseries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: selectedMetric,
          interval: '5m',
          duration: timeRange,
          aggregation: 'avg'
        })
      });
      if (tsResponse.ok) {
        const tsData = await tsResponse.json();
        setTimeSeries(tsData.series || []);
      }

      // Fetch active alerts
      const alertsResponse = await fetch('http://localhost:8001/api/v3/metrics/alerts/active');
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json();
        setAlerts(alertsData.alerts || []);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setLoading(false);
    }
  };

  const formatValue = (value: number | null, metric: string) => {
    if (value === null || value === undefined) return 'N/A';
    
    if (metric.includes('rate') || metric.includes('usage')) {
      return `${value.toFixed(1)}%`;
    }
    return value.toFixed(0);
  };

  const getMetricIcon = (metric: string) => {
    if (metric.includes('cpu')) return <Cpu className="h-4 w-4" />;
    if (metric.includes('memory')) return <MemoryStick className="h-4 w-4" />;
    if (metric.includes('disk')) return <HardDrive className="h-4 w-4" />;
    if (metric.includes('network')) return <Network className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  const getTrendIcon = (current: number, previous: number) => {
    if (!previous || current === previous) return null;
    if (current > previous) {
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    }
    return <TrendingDown className="h-4 w-4 text-red-500" />;
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading metrics...</div>
      </div>
    );
  }

  const chartData = timeSeries
    .filter(point => point.value !== null)
    .map(point => ({
      time: new Date(point.timestamp).toLocaleTimeString(),
      value: point.value
    }));

  const pieData = summary ? [
    { name: 'Active', value: summary.agents.active || 0, color: '#10b981' },
    { name: 'Inactive', value: (summary.agents.total || 0) - (summary.agents.active || 0), color: '#e5e7eb' }
  ] : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="h-6 w-6" />
          Metrics & Monitoring
        </h2>
        <div className="flex gap-2">
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="tasks.success_rate">Success Rate</option>
            <option value="agents.active">Active Agents</option>
            <option value="resources.cpu_usage">CPU Usage</option>
            <option value="resources.memory_usage">Memory Usage</option>
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
        </div>
      </div>

      {/* Active Alerts */}
      {alerts.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              Active Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.map((alert, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-white rounded-md">
                  <div className="flex items-center gap-3">
                    {getMetricIcon(alert.metric)}
                    <span className="font-medium">{alert.metric}</span>
                    <Badge variant="destructive">{alert.violation}</Badge>
                  </div>
                  <div className="text-sm text-gray-600">
                    {formatValue(alert.value, alert.metric)} • {new Date(alert.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summary && (
          <>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Active Agents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summary.agents.active || 0} / {summary.agents.total || 0}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {summary.agents.total > 0 
                    ? `${((summary.agents.active / summary.agents.total) * 100).toFixed(0)}% active`
                    : 'No agents'}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Success Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold flex items-center gap-2">
                  {formatValue(summary.tasks.success_rate, 'rate')}
                  {summary.tasks.success_rate >= 95 ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {summary.tasks.pending || 0} tasks pending
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">CPU Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(summary.resources.cpu_usage, 'usage')}
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      summary.resources.cpu_usage < 60 
                        ? 'bg-green-500' 
                        : summary.resources.cpu_usage < 80 
                        ? 'bg-yellow-500' 
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(summary.resources.cpu_usage || 0, 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Memory Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(summary.resources.memory_usage, 'usage')}
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      summary.resources.memory_usage < 60 
                        ? 'bg-green-500' 
                        : summary.resources.memory_usage < 80 
                        ? 'bg-yellow-500' 
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(summary.resources.memory_usage || 0, 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Time Series Chart */}
      <Card>
        <CardHeader>
          <CardTitle>
            {selectedMetric.split('.').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ')} - {timeRange}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  domain={selectedMetric.includes('rate') || selectedMetric.includes('usage') ? [0, 100] : undefined}
                />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-500">
              No data available for the selected time range
            </div>
          )}
        </CardContent>
      </Card>

      {/* Agent Distribution */}
      {summary && summary.agents.total > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Agent Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Avg Response Time</span>
                  <span className="font-medium">145ms</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Throughput</span>
                  <span className="font-medium">1,234 req/s</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Error Rate</span>
                  <span className="font-medium">0.02%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Uptime</span>
                  <span className="font-medium">99.98%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}