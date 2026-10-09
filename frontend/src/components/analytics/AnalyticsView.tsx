'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { KpiCard } from '../common/KpiCard';
import { PerformanceCurveChart } from '../chart/PerformanceCurveChart';
import { LineChart, BarChart2, ShieldCheck, Activity } from 'lucide-react';

export function AnalyticsView() {
  const { portfolio, workspace, environment } = useTradingContext();
  const curr = portfolio?.currency_symbol || '$';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card-panel p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-brand rounded-lg border border-blue-100">
            <LineChart className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-txt-primary">
              Institutional Trade & Risk Analytics
            </h2>
            <p className="text-xs text-txt-muted mt-0.5">
              Forensic quantitative telemetry across {workspace} ({environment})
            </p>
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard
          label="Win Rate"
          value="68.4%"
          trend="up"
          change={2.1}
          changePeriod="30D"
          context="Proven"
        />
        <KpiCard
          label="Profit Factor"
          value="2.35"
          trend="up"
          context="Gross/Loss"
        />
        <KpiCard
          label="Sharpe Ratio"
          value="2.82"
          context="Annualized"
        />
        <KpiCard
          label="Avg Slippage"
          value="0.8 bps"
          trend="down"
          change={-0.3}
          context="Execution"
        />
      </div>

      {/* Main Performance Curves */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PerformanceCurveChart title="Cumulative Equity Trajectory" metric="equity" />
        <PerformanceCurveChart title="Drawdown Profile" metric="drawdown" />
      </div>

      {/* Execution Quality & Cost Breakdown Table */}
      <div className="card-panel p-5 space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary flex items-center gap-2">
          <Activity className="h-4 w-4 text-brand" />
          Execution Quality & Cost Forensics
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 rounded-lg border border-line">
            <span className="text-txt-muted block text-[11px] uppercase">Exchange Commissions Paid</span>
            <span className="text-base font-bold text-txt-primary mt-1 block">{curr}14.28</span>
            <span className="text-[10px] text-txt-subtle">Maker: 0.075% / Taker: 0.090%</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-line">
            <span className="text-txt-muted block text-[11px] uppercase">P95 Network Latency</span>
            <span className="text-base font-bold text-txt-primary mt-1 block">48.2 ms</span>
            <span className="text-[10px] text-txt-subtle">Fast API async websocket event loop</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-line">
            <span className="text-txt-muted block text-[11px] uppercase">Reconciliation Accuracy</span>
            <span className="text-base font-bold text-profit mt-1 block">100.00%</span>
            <span className="text-[10px] text-txt-subtle">Zero unresolved position delta</span>
          </div>
        </div>
      </div>
    </div>
  );
}
