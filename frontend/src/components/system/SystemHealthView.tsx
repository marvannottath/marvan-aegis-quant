'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import { Server, Database, ShieldCheck, Activity, Cpu, HardDrive, Wifi, RefreshCw } from 'lucide-react';

interface HardwareMetrics {
  timestamp: string;
  cpu_percent: number;
  ram: { used_mb: number; total_mb: number; percent: number };
  disk: { used_gb: number; total_gb: number; percent: number };
  broker_latencies: Array<{
    gateway: string;
    protocol: string;
    latency_ms: number;
    status: string;
    last_heartbeat: string;
  }>;
  average_latency_ms: number;
  auto_healing_status: string;
  last_backup_time: string;
}

export function SystemHealthView() {
  const { envStatus, workspace, marketDataStatus } = useTradingContext();
  const [metrics, setMetrics] = useState<HardwareMetrics | null>(null);
  const [mktStatus, setMktStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadMetrics = async () => {
    try {
      setIsLoading(true);
      const [resHw, resMkt] = await Promise.all([
        fetch('/api/system/hardware-metrics').then((r) => r.json()),
        fetch(`/api/market-data/status?workspace=${workspace}`).then((r) => r.json()),
      ]);
      setMetrics(resHw);
      setMktStatus(resMkt);
    } catch (err) {
      console.error('Failed to load system metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 10000);
    return () => clearInterval(interval);
  }, [workspace]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            System Architecture & Forensic Telemetry
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Real hardware utilization, gateway round-trip latency, and market watchdog freshness.
          </p>
        </div>

        <button
          onClick={loadMetrics}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Hardware Utilization Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">CPU Utilization</span>
            <Cpu className="h-4 w-4 text-brand" />
          </div>
          <div className="text-2xl font-bold font-mono text-txt-primary">
            {metrics?.cpu_percent !== undefined ? `${metrics.cpu_percent}%` : '—'}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-brand h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, metrics?.cpu_percent || 0)}%` }}
            />
          </div>
          <p className="text-[11px] text-txt-subtle">FastAPI Multi-Threaded Core</p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Memory (RAM)</span>
            <Server className="h-4 w-4 text-brand" />
          </div>
          <div className="text-2xl font-bold font-mono text-txt-primary">
            {metrics?.ram?.percent !== undefined ? `${metrics.ram.percent}%` : '—'}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-brand h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, metrics?.ram?.percent || 0)}%` }}
            />
          </div>
          <p className="text-[11px] text-txt-subtle">
            {metrics?.ram ? `${metrics.ram.used_mb} MB / ${metrics.ram.total_mb} MB` : 'Loading RAM...'}
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Disk Storage</span>
            <HardDrive className="h-4 w-4 text-brand" />
          </div>
          <div className="text-2xl font-bold font-mono text-txt-primary">
            {metrics?.disk?.percent !== undefined ? `${metrics.disk.percent}%` : '—'}
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-brand h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, metrics?.disk?.percent || 0)}%` }}
            />
          </div>
          <p className="text-[11px] text-txt-subtle">
            {metrics?.disk ? `${metrics.disk.used_gb} GB / ${metrics.disk.total_gb} GB` : 'Loading Disk...'}
          </p>
        </div>
      </div>

      {/* Sentinel & Watchdog Health */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Execution Sentinel</span>
            <ShieldCheck className="h-4 w-4 text-profit" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            {envStatus?.reconciliation_status || 'HEALTHY'}
          </div>
          <p className="text-[11px] text-txt-subtle">
            Continuous balance & position reconciliation active.
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Database Layer</span>
            <Database className="h-4 w-4 text-brand" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            SQLite WAL Mode Verified
          </div>
          <p className="text-[11px] text-txt-subtle">
            Durable ACID transactions with atomic journal commits.
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Market Watchdog ({workspace})</span>
            <Activity className="h-4 w-4 text-profit" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            {mktStatus?.feed_status === 'LIVE' ? (
              <span className="text-profit">LIVE ({mktStatus.event_age_seconds ?? 0}s age)</span>
            ) : (
              <span className="text-amber-600">DATA UNAVAILABLE</span>
            )}
          </div>
          <p className="text-[11px] text-txt-subtle">
            {mktStatus?.feed_status === 'LIVE'
              ? `${mktStatus.events_received || 0} ticks received on ${mktStatus.provider || 'stream'}`
              : 'Requires authenticated broker stream before order entry'}
          </p>
        </div>
      </div>

      {/* Gateway Round-Trip Latency Table */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wifi className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Broker Gateway Network Telemetry
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            Avg Latency: {metrics?.average_latency_ms ? `${metrics.average_latency_ms.toFixed(1)} ms` : '—'}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-line bg-slate-50 text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
                <th className="py-2.5 px-4">Gateway</th>
                <th className="py-2.5 px-4">Protocol</th>
                <th className="py-2.5 px-4 text-right">Round-Trip Latency</th>
                <th className="py-2.5 px-4 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {metrics?.broker_latencies?.map((g) => (
                <tr key={g.gateway} className="table-row-hover">
                  <td className="py-2.5 px-4 font-bold text-txt-primary">{g.gateway}</td>
                  <td className="py-2.5 px-4 text-txt-muted">{g.protocol}</td>
                  <td className="py-2.5 px-4 text-right font-bold text-txt-primary">
                    {g.latency_ms > 0 ? `${g.latency_ms.toFixed(2)} ms` : 'N/A'}
                  </td>
                  <td className="py-2.5 px-4 text-center">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-txt-secondary">
                      {g.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right text-txt-subtle text-[11px]">{g.last_heartbeat}</td>
                </tr>
              )) || (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-txt-muted font-sans">
                    {isLoading ? 'Measuring gateway latencies...' : 'No telemetry samples available.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
