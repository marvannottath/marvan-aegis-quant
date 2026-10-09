'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import { Server, Database, ShieldCheck, Activity } from 'lucide-react';

export function SystemHealthView() {
  const { envStatus } = useTradingContext();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          System Architecture & Forensic Health
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Backend thread telemetry, SQLite WAL synchronization, and Sentinel integrity status.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Execution Sentinel</span>
            <ShieldCheck className="h-4 w-4 text-profit" />
          </div>
          <div className="text-lg font-bold font-mono text-txt-primary">
            {envStatus?.reconciliation_status || 'HEALTHY'}
          </div>
          <p className="text-[11px] text-txt-subtle">
            Continuous 3-way balance and position reconciliation.
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Database Layer</span>
            <Database className="h-4 w-4 text-brand" />
          </div>
          <div className="text-lg font-bold font-mono text-txt-primary">
            SQLite WAL Mode
          </div>
          <p className="text-[11px] text-txt-subtle">
            ACID transaction durability with synchronized JSON mirrors.
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Market Data Watchdog</span>
            <Activity className="h-4 w-4 text-profit" />
          </div>
          <div className="text-lg font-bold font-mono text-txt-primary">
            Freshness: &lt; {envStatus?.stale_threshold_seconds || 5.0}s
          </div>
          <p className="text-[11px] text-txt-subtle">
            Fail-closed order blocking on stale ticks.
          </p>
        </div>
      </div>
    </div>
  );
}
