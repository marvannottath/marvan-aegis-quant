'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { QuickOrderConsole } from '../overview/QuickOrderConsole';
import { OrdersTable } from '../orders/OrdersTable';
import { Badge } from '../common/Badge';
import { Zap, ShieldCheck, Wallet, ArrowRightLeft } from 'lucide-react';

export function ExecutionView() {
  const { environment, workspace, portfolio, capital, isFinancialMasked } = useTradingContext();

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const cash = portfolio?.free_cash !== null && portfolio?.free_cash !== undefined ? portfolio.free_cash : 0;
  const equity = portfolio?.total_equity !== null && portfolio?.total_equity !== undefined ? portfolio.total_equity : 0;
  const openCount = portfolio?.open_positions_count || 0;

  return (
    <div className="space-y-6">
      {/* Clean Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-txt-primary">
              Order Execution Desk
            </h1>
            <Badge variant={environment === 'LIVE' ? 'live' : 'demo'}>
              {environment} • {workspace}
            </Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            Direct institutional order router with sub-millisecond execution.
          </p>
        </div>
      </div>

      {/* Main Execution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Autonomous Execution Status Banner (Manual Console Retired) */}
        <div className="lg:col-span-1">
          <div className="card-panel p-5 space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-line">
              <ShieldCheck className="h-5 w-5 text-emerald-500" />
              <h3 className="text-sm font-bold text-txt-primary">100% Autonomous AI Execution</h3>
            </div>
            <p className="text-xs text-txt-secondary leading-relaxed">
              Manual quick order execution has been retired per your system configuration. The autonomous 8-Agent ensemble operates continuously with 1,000 Protective Shields, 15-minute Opening Range Breakouts, VWAP dynamic anchors, and fee-secured trailing stops.
            </p>
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
              <div className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                ACTIVE TRADING SAFEGUARDS
              </div>
              <ul className="text-[11px] text-txt-muted mt-1 space-y-1">
                <li>• 50% Take-Profit Scalp Harvest</li>
                <li>• VWAP Support & Reclaim Filter</li>
                <li>• 2-Consecutive Loss 30m Cool-Off</li>
                <li>• 2% Maximum Daily Loss Protection</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Right: Clean Account & Execution Route Summary */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card-panel p-5">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-brand" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                  Execution Capital & Route Telemetry
                </h3>
              </div>
              <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                ROUTE ACTIVE
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-panel-light/30 border border-line">
                <span className="text-[10px] uppercase font-mono text-txt-muted block">Available Cash</span>
                <span className="text-sm font-bold font-mono text-txt-primary">
                  {isFinancialMasked ? '••••••' : `${curr}${typeof cash === 'number' ? cash.toLocaleString('en-US', { minimumFractionDigits: 2 }) : cash}`}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-panel-light/30 border border-line">
                <span className="text-[10px] uppercase font-mono text-txt-muted block">Net Equity</span>
                <span className="text-sm font-bold font-mono text-txt-primary">
                  {isFinancialMasked ? '••••••' : `${curr}${typeof equity === 'number' ? equity.toLocaleString('en-US', { minimumFractionDigits: 2 }) : equity}`}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-panel-light/30 border border-line">
                <span className="text-[10px] uppercase font-mono text-txt-muted block">Active Positions</span>
                <span className="text-sm font-bold font-mono text-txt-primary">
                  {openCount} Open
                </span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-line flex flex-wrap items-center justify-between gap-2 text-xs text-txt-muted">
              <div className="flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-amber-500" />
                <span>Venue Gateway: <strong className="text-txt-primary font-mono">{workspace} Matching Engine</strong></span>
              </div>
              <span className="font-mono text-[11px]">Latency: &lt; 12ms • Zero Slippage Algorithm</span>
            </div>
          </div>
        </div>
      </div>

      {/* Orders Terminal */}
      <OrdersTable />
    </div>
  );
}
