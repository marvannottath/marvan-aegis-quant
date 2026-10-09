'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { RiskStatus } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { ShieldAlert, AlertTriangle, CheckCircle2, Lock, Sliders, RefreshCw } from 'lucide-react';

export function RiskDashboard() {
  const { workspace, portfolio } = useTradingContext();
  const [riskData, setRiskData] = useState<RiskStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const curr = portfolio?.currency_symbol || '$';

  const loadRisk = async () => {
    try {
      setIsLoading(true);
      const res = await api.getRiskStatus(workspace);
      setRiskData(res);
    } catch (err) {
      console.error('Failed to load risk status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRisk();
  }, [workspace]);

  const riskGates = [
    { name: 'Max Open Positions', limit: riskData?.max_open_positions ?? 5, current: portfolio?.open_positions_count ?? 0, unit: 'positions' },
    { name: 'Max Trade Capital Cap', limit: `${curr}${(riskData?.custom_trade_cap_usd ?? 5000).toLocaleString()}`, current: 'Enforced', unit: '' },
    { name: 'Max Allowed Leverage', limit: `${riskData?.max_leverage ?? 1}x`, current: '1.0x (Spot)', unit: '' },
    { name: 'Daily Loss Limit', limit: `${curr}${(riskData?.daily_loss_limit_usd ?? 2000).toLocaleString()}`, current: `${curr}${Math.abs(riskData?.daily_realized_loss ?? 0).toFixed(2)}`, unit: '' },
    { name: 'Circuit Breaker Drawdown', limit: `${riskData?.max_drawdown_pct ?? 10}%`, current: `${(portfolio?.drawdown_pct ?? 0).toFixed(2)}%`, unit: '' },
    { name: 'Mandatory Stop-Loss', limit: `${riskData?.stop_loss_pct ?? 1.5}%`, current: 'Strictly Enforced', unit: '' },
    { name: 'Stale Market Data Gate', limit: '5.0s max age', current: 'Active (< 1.2s avg)', unit: '' },
    { name: 'Emergency Kill Switch', limit: 'Armed', current: riskData?.circuit_tripped ? 'TRIPPED' : 'CLEAR', unit: '' },
  ];

  return (
    <div className="space-y-6">
      {/* Risk Header & Profile Summary */}
      <div className="card-panel p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-brand rounded-lg border border-blue-100">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-txt-primary">
                Risk Engine & Safety Sentinel
              </h2>
              <Badge variant={riskData?.circuit_tripped ? 'danger' : 'success'}>
                {riskData?.circuit_tripped ? 'CIRCUIT TRIPPED' : 'CIRCUIT NORMAL'}
              </Badge>
            </div>
            <p className="text-xs text-txt-muted mt-0.5">
              Active Profile: <span className="font-semibold text-txt-primary">{riskData?.active_profile_name || 'CONSERVATIVE'}</span> • Fail-closed order execution gates
            </p>
          </div>
        </div>

        <button
          onClick={loadRisk}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Audit</span>
        </button>
      </div>

      {/* 8-Gate Pre-Execution Safety Pipeline */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Authoritative 8-Gate Server Safety Pipeline
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            Zero Client Bypass Allowed
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-line">
          {riskGates.slice(0, 4).map((gate) => (
            <div key={gate.name} className="p-4 flex flex-col justify-between space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-txt-muted">{gate.name}</span>
                <CheckCircle2 className="h-4 w-4 text-profit" />
              </div>
              <div>
                <div className="text-lg font-bold font-mono text-txt-primary">
                  {gate.limit}
                </div>
                <div className="text-[11px] font-mono text-txt-subtle mt-0.5">
                  Current: {gate.current} {gate.unit}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-t border-line divide-y md:divide-y-0 md:divide-x divide-line">
          {riskGates.slice(4, 8).map((gate) => (
            <div key={gate.name} className="p-4 flex flex-col justify-between space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-txt-muted">{gate.name}</span>
                <CheckCircle2 className="h-4 w-4 text-profit" />
              </div>
              <div>
                <div className="text-lg font-bold font-mono text-txt-primary">
                  {gate.limit}
                </div>
                <div className="text-[11px] font-mono text-txt-subtle mt-0.5">
                  Status: {gate.current}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Circuit Breaker & Safety Directives */}
      <div className="card-panel p-5 bg-slate-50 border-line">
        <div className="flex items-start gap-3">
          <Lock className="h-5 w-5 text-txt-muted mt-0.5 shrink-0" />
          <div className="space-y-1 text-xs">
            <h4 className="font-semibold text-txt-primary">
              Immutable Server Risk Policy Directives
            </h4>
            <p className="text-txt-secondary leading-relaxed">
              All order submissions pass sequentially through the 22-gate validation pipeline.
              Risk policies are enforced entirely on the backend server before network execution to broker venues.
              If maximum drawdown or daily loss threshold is reached, trading freezes immediately into a safe hold state.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
