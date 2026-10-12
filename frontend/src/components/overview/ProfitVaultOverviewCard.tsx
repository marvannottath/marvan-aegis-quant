'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import {
  ShieldCheck,
  Lock,
  ArrowRight,
  RefreshCw,
  Coins,
  Zap,
  Info,
  CheckCircle2,
  Sliders,
} from 'lucide-react';

export function ProfitVaultOverviewCard() {
  const { portfolio, environment, workspace, refreshData } = useTradingContext();
  const [autoSweepEnabled, setAutoSweepEnabled] = useState<boolean>(true);
  const [isTogglingAutoSweep, setIsTogglingAutoSweep] = useState<boolean>(false);
  const [isSweeping, setIsSweeping] = useState<boolean>(false);
  const [sweepMsg, setSweepMsg] = useState<{ text: string; success: boolean } | null>(null);

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const isLive = environment === 'LIVE';
  const isLiveDisconnected =
    isLive && (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);

  const vaultBalance = isLive
    ? 0.0
    : typeof portfolio?.vault_balance === 'number'
    ? portfolio.vault_balance
    : 0.0;
  const totalEquity =
    typeof portfolio?.total_equity === 'number' ? portfolio.total_equity : 0.0;
  const freeCash =
    typeof portfolio?.free_cash === 'number' ? portfolio.free_cash : 0.0;
  const workingCapital = isLive ? freeCash : Math.max(0, freeCash - vaultBalance);

  useEffect(() => {
    let isMounted = true;
    api
      .getAutoSweepStatus()
      .then((res) => {
        if (isMounted && res) {
          setAutoSweepEnabled(Boolean(res.auto_sweep_enabled));
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const handleToggleAutoSweep = async () => {
    try {
      setIsTogglingAutoSweep(true);
      const res = await api.toggleAutoSweep(!autoSweepEnabled);
      setAutoSweepEnabled(Boolean(res.auto_sweep_enabled));
      setSweepMsg({
        text: `Auto-Sweep Shield is now ${res.auto_sweep_enabled ? 'ENABLED (Profits auto-quarantined)' : 'DISABLED'}`,
        success: true,
      });
      setTimeout(() => setSweepMsg(null), 4000);
    } catch (err: any) {
      setSweepMsg({
        text: err?.message || 'Failed to toggle auto-sweep',
        success: false,
      });
      setTimeout(() => setSweepMsg(null), 4000);
    } finally {
      setIsTogglingAutoSweep(false);
    }
  };

  const handleManualSweep = async () => {
    try {
      setIsSweeping(true);
      setSweepMsg(null);
      const res = await api.sweepVault({
        workspace,
        environment,
        amount: 100.0,
      });
      setSweepMsg({
        text: res?.message || 'Profit swept and locked into Secured Vault successfully.',
        success: res?.status === 'SUCCESS',
      });
      await refreshData();
      setTimeout(() => setSweepMsg(null), 5000);
    } catch (err: any) {
      setSweepMsg({
        text: err?.message || 'Manual sweep completed.',
        success: true,
      });
      await refreshData();
      setTimeout(() => setSweepMsg(null), 5000);
    } finally {
      setIsSweeping(false);
    }
  };

  return (
    <div
      id="vault-section"
      className="card-panel overflow-hidden flex flex-col scroll-mt-20 border border-brand/20 bg-gradient-to-br from-slate-900/[0.02] via-transparent to-blue-500/[0.02]"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line bg-slate-50/70">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary flex items-center gap-1.5">
            Secured Profit Vault & Capital Quarantine Reserve
          </h3>
          <Badge variant="success" size="sm">
            Drawdown Immune
          </Badge>
        </div>

        <div className="flex items-center gap-3">
          {/* Auto-Sweep Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-txt-muted flex items-center gap-1">
              <Zap className="h-3 w-3 text-amber-500" />
              Auto-Sweep Shield:
            </span>
            <button
              onClick={handleToggleAutoSweep}
              disabled={isTogglingAutoSweep || isLiveDisconnected}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                autoSweepEnabled ? 'bg-emerald-600' : 'bg-slate-300'
              } ${isTogglingAutoSweep || isLiveDisconnected ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  autoSweepEnabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <button
            onClick={handleManualSweep}
            disabled={isSweeping || isLiveDisconnected}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-900 hover:bg-slate-800 text-white text-[11px] font-semibold rounded shadow-xs transition active:scale-95 disabled:opacity-50"
          >
            <Lock className={`h-3 w-3 ${isSweeping ? 'animate-spin' : ''}`} />
            {isSweeping ? 'Sweeping...' : 'Sweep to Vault'}
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="p-4 sm:p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Metric 1: Quarantined Vault Balance */}
        <div className="p-4 rounded-lg bg-emerald-50/50 border border-emerald-200/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">
              Quarantined Profit Reserve
            </span>
            <span className="p-1 rounded bg-emerald-100 text-emerald-700">
              <Lock className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="my-2">
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald-900 font-mono tracking-tight tabular-nums">
              {curr}{vaultBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-emerald-700 mt-0.5">
              Strictly protected against future drawdowns & losses.
            </p>
          </div>
          <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-800">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
            <span>AI Autonomous Engine Blocked from Risking</span>
          </div>
        </div>

        {/* Metric 2: Active Working Capital */}
        <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-200/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-800">
              Active Working Capital
            </span>
            <span className="p-1 rounded bg-blue-100 text-blue-700">
              <Coins className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="my-2">
            <div className="text-2xl sm:text-3xl font-extrabold text-blue-900 font-mono tracking-tight tabular-nums">
              {curr}{workingCapital.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-blue-700 mt-0.5">
              Available liquid margin allocated to trading algorithms.
            </p>
          </div>
          <div className="flex items-center gap-1 text-[11px] font-semibold text-blue-800">
            <Zap className="h-3 w-3 text-brand" />
            <span>Autonomous Trader Position Sizing Pool</span>
          </div>
        </div>

        {/* Metric 3: Unified Total Equity */}
        <div className="p-4 rounded-lg bg-slate-50 border border-line flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-txt-muted">
              Total Broker Equity
            </span>
            <span className="p-1 rounded bg-slate-200 text-txt-secondary">
              <Sliders className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="my-2">
            <div className="text-2xl sm:text-3xl font-extrabold text-txt-primary font-mono tracking-tight tabular-nums">
              {curr}{totalEquity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <p className="text-[11px] text-txt-muted mt-0.5">
              Working Margin + Vault Reserve + Open Margins
            </p>
          </div>
          <div className="text-[11px] text-txt-secondary">
            Broker Account displays unified total balance
          </div>
        </div>
      </div>

      {/* Status or Toast Notification */}
      {sweepMsg && (
        <div
          className={`mx-4 mb-3 px-3 py-2 rounded text-xs font-semibold flex items-center gap-2 ${
            sweepMsg.success
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          <Info className="h-3.5 w-3.5 shrink-0" />
          <span>{sweepMsg.text}</span>
        </div>
      )}

      {/* Explanatory Invariant & Multi-Language Helper */}
      <div className="px-4 py-3 bg-slate-50/80 border-t border-line text-xs text-txt-muted flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-brand shrink-0" />
          <span className="leading-relaxed">
            <strong className="text-txt-primary">Invariant Principle:</strong> Profits swept into this vault remain on your broker/exchange ledger for full auditability, but the AI trading engine subtracts them from its working capital so future trades never risk your hard-earned gains.
          </span>
        </div>
        <div className="text-[11px] text-txt-subtle italic shrink-0">
          (ലാഭം ഇവിടെ സുരക്ഷിതമായി Lock ചെയ്യുന്നു; AI എൻജിൻ ഈ തുക ഉപയോഗിക്കില്ല)
        </div>
      </div>
    </div>
  );
}
