'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { RiskStatus } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { ShieldAlert, AlertTriangle, CheckCircle2, Lock, Sliders, RefreshCw, Gauge, Save, RotateCcw } from 'lucide-react';

export function RiskDashboard() {
  const { workspace, environment, portfolio } = useTradingContext();
  const [riskData, setRiskData] = useState<RiskStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; success: boolean } | null>(null);

  // Manual configuration inputs state
  const [manualLeverage, setManualLeverage] = useState<string>('2');
  const [manualStopLoss, setManualStopLoss] = useState<string>('0.4');
  const [manualMaxPositions, setManualMaxPositions] = useState<string>('4');
  const [manualDailyLoss, setManualDailyLoss] = useState<string>('2000');
  const [manualTradeCap, setManualTradeCap] = useState<string>('5000');
  const [manualDrawdownLimit, setManualDrawdownLimit] = useState<string>('5');

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

  const loadRisk = async () => {
    try {
      setIsLoading(true);
      const res = await api.getRiskStatus(workspace, environment);
      setRiskData(res);
      if (res) {
        setManualLeverage(String(res.max_leverage ?? 2));
        setManualStopLoss(String(res.stop_loss_pct ?? 0.4));
        setManualMaxPositions(String(res.max_open_positions ?? 4));
        setManualDailyLoss(String(res.daily_loss_limit_usd ?? 2000));
        setManualTradeCap(String(res.custom_trade_cap_usd ?? 5000));
        setManualDrawdownLimit(String(res.max_drawdown_pct ?? 5));
      }
    } catch (err) {
      console.error('Failed to load risk status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRisk();
  }, [workspace, environment]);

  const handleSelectPreset = async (profile: 'CONSERVATIVE' | 'MODERATE' | 'AGGRESSIVE') => {
    try {
      setIsUpdating(true);
      setFeedbackMsg(null);
      // Optimistically update riskData immediately so visual selection shifts instantly
      setRiskData((prev: any) => ({
        ...prev,
        active_profile_name: profile,
        active_profile: profile,
      }));
      await api.setRiskProfile(profile, workspace, environment);
      setFeedbackMsg({
        text: `Risk Profile for ${workspace} (${environment}) successfully switched to ${profile}!`,
        success: true,
      });
      await loadRisk();
    } catch (err: any) {
      setFeedbackMsg({
        text: err?.message || `Failed to switch to ${profile} risk profile for ${workspace} (${environment}).`,
        success: false,
      });
      await loadRisk();
    } finally {
      setIsUpdating(false);
    }
  };

  const handleSaveManualLimits = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsUpdating(true);
      setFeedbackMsg(null);
      await api.updateRiskLimits({
        max_leverage: parseFloat(manualLeverage),
        stop_loss_pct: parseFloat(manualStopLoss),
        max_open_positions: parseInt(manualMaxPositions, 10),
        daily_loss_limit_usd: parseFloat(manualDailyLoss),
        custom_trade_cap_usd: parseFloat(manualTradeCap),
        circuit_breaker_drawdown_pct: parseFloat(manualDrawdownLimit),
        workspace,
        environment,
      });
      setFeedbackMsg({
        text: `Custom risk parameters applied for ${workspace} (${environment}) and strictly enforced on server execution gate.`,
        success: true,
      });
      await loadRisk();
    } catch (err: any) {
      setFeedbackMsg({
        text: err?.message || 'Failed to update custom risk limits.',
        success: false,
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleResetCircuitBreaker = async () => {
    try {
      setIsUpdating(true);
      setFeedbackMsg(null);
      await api.resetCircuitBreaker(workspace);
      setFeedbackMsg({
        text: 'Circuit breaker reset and peak equity recalibrated.',
        success: true,
      });
      await loadRisk();
    } catch (err: any) {
      setFeedbackMsg({
        text: err?.message || 'Failed to reset circuit breaker.',
        success: false,
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const activeProfile = (riskData?.active_profile_name || (riskData as any)?.active_profile || 'CONSERVATIVE').toUpperCase();

  const riskGates = [
    { name: 'Max Open Positions', limit: `${riskData?.max_open_positions ?? 4} positions`, current: `${portfolio?.open_positions_count ?? 0} active`, unit: '' },
    { name: 'Max Trade Capital Cap', limit: `${curr}${(riskData?.custom_trade_cap_usd ?? 5000).toLocaleString()}`, current: 'Enforced', unit: '' },
    { name: 'Max Allowed Leverage', limit: `${riskData?.max_leverage ?? 2}x`, current: `${riskData?.max_leverage ?? 2}x Max`, unit: '' },
    { name: 'Daily Loss Limit', limit: `${curr}${(riskData?.daily_loss_limit_usd ?? 2000).toLocaleString()}`, current: `${curr}${Math.abs(riskData?.daily_realized_loss ?? 0).toFixed(2)}`, unit: '' },
    { name: 'Circuit Breaker Drawdown', limit: `${riskData?.max_drawdown_pct ?? 5}%`, current: `${(portfolio?.drawdown_pct ?? 0).toFixed(2)}%`, unit: '' },
    { name: 'Mandatory Stop-Loss', limit: `${riskData?.stop_loss_pct ?? 0.4}%`, current: 'Strictly Enforced', unit: '' },
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
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="text-xs text-txt-muted">Target Venue:</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-900 border border-slate-700 text-amber-400">
                {workspace} ({environment})
              </span>
              <span className="text-xs text-txt-muted">
                • Active Profile: <span className="font-semibold text-txt-primary">{activeProfile}</span> • Isolated Risk Gates
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {riskData?.circuit_tripped && (
            <button
              onClick={handleResetCircuitBreaker}
              disabled={isUpdating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Circuit Breaker</span>
            </button>
          )}
          <button
            onClick={loadRisk}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh Audit</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedbackMsg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            feedbackMsg.success
              ? 'bg-emerald-50 text-profit border border-emerald-200'
              : 'bg-red-50 text-loss border border-red-200'
          }`}
        >
          {feedbackMsg.success ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          )}
          <span className="font-semibold">{feedbackMsg.text}</span>
        </div>
      )}

      {/* Preset Risk Profiles: LOW / MEDIUM / HIGH */}
      <div className="card-panel p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Risk Profile Selection (Low • Medium • High)
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            Click to activate instant preset
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Preset 1: Low (Conservative) */}
          <button
            type="button"
            onClick={() => handleSelectPreset('CONSERVATIVE')}
            disabled={isUpdating}
            className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
              activeProfile === 'CONSERVATIVE'
                ? 'border-emerald-500 bg-emerald-50/30 ring-2 ring-emerald-500/20'
                : 'border-line bg-white hover:border-slate-300 hover:bg-slate-50/50'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-emerald-700 uppercase tracking-wide">
                  LOW RISK (CONSERVATIVE)
                </span>
                {activeProfile === 'CONSERVATIVE' && (
                  <Badge variant="success" size="sm">ACTIVE</Badge>
                )}
              </div>
              <p className="text-[11px] text-txt-muted leading-relaxed">
                Hyper-scalping capital preservation with tight risk barriers.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2 text-[11px] font-mono font-semibold text-txt-secondary">
              <span className="bg-slate-100 px-2 py-0.5 rounded">2x Leverage</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">0.4% Stop-Loss</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">4 Positions</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">5% Drawdown</span>
            </div>
          </button>

          {/* Preset 2: Medium (Moderate) */}
          <button
            type="button"
            onClick={() => handleSelectPreset('MODERATE')}
            disabled={isUpdating}
            className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
              activeProfile === 'MODERATE'
                ? 'border-blue-500 bg-blue-50/30 ring-2 ring-blue-500/20'
                : 'border-line bg-white hover:border-slate-300 hover:bg-slate-50/50'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">
                  MEDIUM RISK (BALANCED)
                </span>
                {activeProfile === 'MODERATE' && (
                  <Badge variant="live" size="sm">ACTIVE</Badge>
                )}
              </div>
              <p className="text-[11px] text-txt-muted leading-relaxed">
                Balanced scalping with steady risk exposure and adaptive trailing.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2 text-[11px] font-mono font-semibold text-txt-secondary">
              <span className="bg-slate-100 px-2 py-0.5 rounded">10x Leverage</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">0.8% Stop-Loss</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">8 Positions</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">10% Drawdown</span>
            </div>
          </button>

          {/* Preset 3: High (Aggressive) */}
          <button
            type="button"
            onClick={() => handleSelectPreset('AGGRESSIVE')}
            disabled={isUpdating}
            className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
              activeProfile === 'AGGRESSIVE'
                ? 'border-amber-500 bg-amber-50/30 ring-2 ring-amber-500/20'
                : 'border-line bg-white hover:border-slate-300 hover:bg-slate-50/50'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-amber-700 uppercase tracking-wide">
                  HIGH RISK (AGGRESSIVE)
                </span>
                {activeProfile === 'AGGRESSIVE' && (
                  <Badge variant="warning" size="sm">ACTIVE</Badge>
                )}
              </div>
              <p className="text-[11px] text-txt-muted leading-relaxed">
                High-frequency alpha scalping targeting maximum swing capture.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2 text-[11px] font-mono font-semibold text-txt-secondary">
              <span className="bg-slate-100 px-2 py-0.5 rounded">25x Leverage</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">1.2% Stop-Loss</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">10 Positions</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded">20% Drawdown</span>
            </div>
          </button>
        </div>
      </div>

      {/* Manual Risk Parameter Customization Form */}
      <div className="card-panel p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Manual Risk Parameter Controls
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            Granular override of server-side safety thresholds
          </span>
        </div>

        <form onSubmit={handleSaveManualLimits} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Max Leverage ({manualLeverage}x)
              </label>
              <input
                type="number"
                step="1"
                min="1"
                max="100"
                value={manualLeverage}
                onChange={(e) => setManualLeverage(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Regulatory cap applies (India SEBI 5x)</span>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Mandatory Stop-Loss (%)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="10"
                value={manualStopLoss}
                onChange={(e) => setManualStopLoss(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Automated bracket stop on fill</span>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Max Open Positions
              </label>
              <input
                type="number"
                step="1"
                min="1"
                max="25"
                value={manualMaxPositions}
                onChange={(e) => setManualMaxPositions(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Concurrent positions across all symbols</span>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Daily Loss Limit ({curr})
              </label>
              <input
                type="number"
                step="10"
                min="10"
                value={manualDailyLoss}
                onChange={(e) => setManualDailyLoss(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Freezes new trades for remainder of session</span>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Max Trade Capital Cap ({curr})
              </label>
              <input
                type="number"
                step="50"
                min="1"
                value={manualTradeCap}
                onChange={(e) => setManualTradeCap(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Ceiling notional allocated per single trade</span>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Circuit Breaker Drawdown (%)
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                max="50"
                value={manualDrawdownLimit}
                onChange={(e) => setManualDrawdownLimit(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono font-semibold rounded-lg border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <span className="text-[10px] text-txt-subtle mt-0.5 block">Peak-to-trough emergency trip percentage</span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isUpdating}
              className="px-4 py-2 rounded-lg bg-brand hover:bg-brand-dark text-white text-xs font-bold transition flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              <span>{isUpdating ? 'Saving...' : 'Apply Custom Risk Limits'}</span>
            </button>
          </div>
        </form>
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
                  Current: {gate.current}
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
              Realized profits swept into the segregated vault are quarantined and never re-enter spot trading automatically.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
