'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Workspace } from '../../lib/types';
import { Play, Pause, AlertOctagon, CheckCircle2, ShieldAlert, Cpu, RefreshCw, LayoutGrid, ChevronDown, ChevronUp } from 'lucide-react';

interface AIAutoTradeControlProps {
  variant?: 'banner' | 'compact' | 'matrix';
}

const ALL_ENGINES: { workspace: Workspace; environment: 'DEMO' | 'LIVE'; label: string; broker: string }[] = [
  { workspace: 'CRYPTO', environment: 'DEMO', label: 'Crypto (Demo)', broker: 'Binance Testnet' },
  { workspace: 'CRYPTO', environment: 'LIVE', label: 'Crypto (Live)', broker: 'Binance Real Spot' },
  { workspace: 'FOREX_GOLD', environment: 'DEMO', label: 'Forex & Gold (Demo)', broker: 'MT5 Demo Pool' },
  { workspace: 'FOREX_GOLD', environment: 'LIVE', label: 'Forex & Gold (Live)', broker: 'MT5 Live Broker' },
  { workspace: 'INDIA', environment: 'DEMO', label: 'Indian Equities (Demo)', broker: 'NSE Virtual Sim' },
  { workspace: 'INDIA', environment: 'LIVE', label: 'Indian Equities (Live)', broker: 'Upstox Real Terminal' },
];

export function AIAutoTradeControl({ variant = 'banner' }: AIAutoTradeControlProps) {
  const { workspace, environment } = useTradingContext();
  const [allStates, setAllStates] = useState<Record<string, any>>({});
  const [showMatrix, setShowMatrix] = useState<boolean>(variant === 'matrix');
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.getAiStatus();
      if (res && res.ai_states) {
        setAllStates(res.ai_states);
      }
    } catch (err) {
      // Quiet fail fallback
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Current active engine state
  const currentKey = `${workspace}:${environment}`;
  const currentStateObj = allStates[currentKey] || allStates[workspace] || {};
  const currentAiState = currentStateObj.state || 'RUNNING';
  const currentReason = currentStateObj.reason || 'Autonomous Cloud Active';
  const isCurrentRunning = currentAiState === 'RUNNING';

  const handleToggleEngine = async (ws: Workspace, env: 'DEMO' | 'LIVE', currentlyRunning: boolean) => {
    const key = `${ws}:${env}`;
    setLoadingKey(key);
    setMessage(null);
    try {
      if (currentlyRunning) {
        await api.pauseAiTrading(ws, env);
        setMessage({ text: `⏸ AI Paused for ${ws} (${env})`, type: 'success' });
      } else {
        const res = await api.resumeAiTrading(ws, env);
        if (res && res.ok === false) {
          setMessage({ text: res.message || res.reason || `Blocked resume for ${ws} (${env})`, type: 'error' });
        } else {
          setMessage({ text: `▶ AI Started for ${ws} (${env})`, type: 'success' });
        }
      }
      await fetchStatus();
    } catch (err: any) {
      setMessage({ text: err.message || `Failed to toggle ${ws} (${env})`, type: 'error' });
    } finally {
      setLoadingKey(null);
    }
  };

  // COMPACT VARIANT (For TopHeader)
  if (variant === 'compact') {
    const isBusy = loadingKey === currentKey;
    return (
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => handleToggleEngine(workspace, environment, isCurrentRunning)}
          disabled={isBusy}
          title={isCurrentRunning ? `Pause AI for ${workspace} (${environment})` : `Start AI for ${workspace} (${environment})`}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border transition shadow-2xs cursor-pointer ${
            isCurrentRunning
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20'
          }`}
        >
          {isBusy ? (
            <RefreshCw className="h-3 w-3 animate-spin" />
          ) : isCurrentRunning ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <Pause className="h-3 w-3" />
              <span className="hidden md:inline">{workspace} ({environment}) Active</span>
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <Play className="h-3 w-3" />
              <span className="hidden md:inline">Start {workspace} ({environment})</span>
            </>
          )}
        </button>
      </div>
    );
  }

  // BANNER / MATRIX VARIANT
  return (
    <div className="w-full bg-panel rounded-xl border border-line p-3 sm:p-4 shadow-xs">
      {/* Current Workspace Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Left: AI Engine Info */}
        <div className="flex items-center gap-3">
          <div
            className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border ${
              isCurrentRunning
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-400'
            }`}
          >
            <Cpu className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-txt-primary">AI Trading Control</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider ${
                  isCurrentRunning
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                    : 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20'
                }`}
              >
                {isCurrentRunning && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />}
                {!isCurrentRunning && <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />}
                {currentAiState}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-txt-secondary border border-line">
                {workspace} • {environment}
              </span>
            </div>

            <p className="text-xs text-txt-secondary mt-0.5">
              {currentReason || (isCurrentRunning ? 'Active order execution & alpha harvest enabled' : 'AI order submissions paused')}
            </p>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {/* Active Workspace Toggle */}
          <button
            onClick={() => handleToggleEngine(workspace, environment, isCurrentRunning)}
            disabled={loadingKey === currentKey}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold rounded-lg border transition shadow-xs cursor-pointer ${
              isCurrentRunning
                ? 'bg-amber-500 text-white border-amber-600 hover:bg-amber-600'
                : 'bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700'
            }`}
          >
            {loadingKey === currentKey ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : isCurrentRunning ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            <span>{isCurrentRunning ? `Pause ${environment}` : `Start ${environment}`}</span>
          </button>

          {/* Toggle All 6 Engines Matrix */}
          <button
            onClick={() => setShowMatrix(!showMatrix)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-line bg-surface hover:bg-slate-50 dark:hover:bg-slate-800 text-txt-secondary transition cursor-pointer"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">All 6 Markets</span>
            {showMatrix ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>
      </div>

      {/* Status Feedback Toast/Notification */}
      {message && (
        <div
          className={`mt-3 px-3 py-1.5 rounded-lg text-xs flex items-center justify-between border ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-700 dark:text-rose-300'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-txt-muted hover:text-txt-primary ml-2 cursor-pointer">
            ✕
          </button>
        </div>
      )}

      {/* 6-MARKET INDEPENDENT ENGINE CONTROL MATRIX */}
      {showMatrix && (
        <div className="mt-4 pt-3.5 border-t border-line">
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-txt-muted">
              Individual Market Engine Isolation (3 Markets × 2 Environments)
            </h4>
            <span className="text-[10px] font-mono text-txt-muted">Independent Pause & Resume</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {ALL_ENGINES.map((eng) => {
              const engKey = `${eng.workspace}:${eng.environment}`;
              const engStateObj = allStates[engKey] || allStates[eng.workspace] || {};
              const engState = engStateObj.state || 'RUNNING';
              const engRunning = engState === 'RUNNING';
              const isEngLoading = loadingKey === engKey;
              const isCurrent = eng.workspace === workspace && eng.environment === environment;

              return (
                <div
                  key={engKey}
                  className={`p-3 rounded-xl border transition flex flex-col justify-between gap-2.5 ${
                    isCurrent
                      ? 'bg-brand/5 border-brand/30 ring-1 ring-brand/20'
                      : 'bg-surface/50 border-line hover:border-line-hover'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-txt-primary">{eng.label}</span>
                        {isCurrent && (
                          <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-brand/15 text-brand">
                            ACTIVE TAB
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-txt-muted block mt-0.5">
                        {eng.broker}
                      </span>
                    </div>

                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider ${
                        engRunning
                          ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                          : 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${engRunning ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                      {engState}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1 border-t border-line/60">
                    {/* Resume / Start Button */}
                    <button
                      onClick={() => handleToggleEngine(eng.workspace, eng.environment, false)}
                      disabled={isEngLoading || engRunning}
                      className={`flex-1 py-1 px-2 rounded-md text-[11px] font-semibold flex items-center justify-center gap-1 transition ${
                        engRunning
                          ? 'opacity-40 bg-slate-100 dark:bg-slate-800 text-txt-muted cursor-not-allowed'
                          : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-2xs cursor-pointer'
                      }`}
                    >
                      <Play className="h-2.5 w-2.5" />
                      <span>Start</span>
                    </button>

                    {/* Pause Button */}
                    <button
                      onClick={() => handleToggleEngine(eng.workspace, eng.environment, true)}
                      disabled={isEngLoading || !engRunning}
                      className={`flex-1 py-1 px-2 rounded-md text-[11px] font-semibold flex items-center justify-center gap-1 transition ${
                        !engRunning
                          ? 'opacity-40 bg-slate-100 dark:bg-slate-800 text-txt-muted cursor-not-allowed'
                          : 'bg-amber-500 hover:bg-amber-600 text-white shadow-2xs cursor-pointer'
                      }`}
                    >
                      <Pause className="h-2.5 w-2.5" />
                      <span>Pause</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
