'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Play, Pause, AlertOctagon, CheckCircle2, ShieldAlert, Cpu, RefreshCw } from 'lucide-react';

interface AIAutoTradeControlProps {
  variant?: 'banner' | 'compact';
}

export function AIAutoTradeControl({ variant = 'banner' }: AIAutoTradeControlProps) {
  const { workspace, environment } = useTradingContext();
  const [aiState, setAiState] = useState<string>('RUNNING');
  const [reason, setReason] = useState<string>('Autonomous Cloud Active');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.getAiStatus();
      if (res && res.ai_states && res.ai_states[workspace]) {
        const current = res.ai_states[workspace];
        setAiState(current.state || 'UNKNOWN');
        setReason(current.reason || '');
        setLastUpdated(new Date().toLocaleTimeString());
      }
    } catch (err) {
      // Quiet fail fallback
    }
  }, [workspace]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 4000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleToggle = async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      if (aiState === 'RUNNING') {
        await api.pauseAiTrading(workspace);
        setAiState('PAUSED');
        setMessage({ text: `AI Auto-Trading PAUSED for ${workspace}`, type: 'success' });
      } else {
        const res = await api.resumeAiTrading(workspace);
        if (res && res.ok === false) {
          setMessage({ text: res.message || 'Preflight gates blocked resume', type: 'error' });
        } else {
          setAiState('RUNNING');
          setMessage({ text: `AI Auto-Trading RESUMED for ${workspace}`, type: 'success' });
        }
      }
      await fetchStatus();
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to toggle AI state', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const isRunning = aiState === 'RUNNING';

  // COMPACT VARIANT (For TopHeader)
  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-1.5">
        <button
          onClick={handleToggle}
          disabled={isLoading}
          title={isRunning ? `Click to Pause AI Trading (${workspace})` : `Click to Start AI Trading (${workspace})`}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border transition shadow-2xs cursor-pointer ${
            isRunning
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20'
          }`}
        >
          {isLoading ? (
            <RefreshCw className="h-3 w-3 animate-spin" />
          ) : isRunning ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <Pause className="h-3 w-3" />
              <span className="hidden md:inline">AI Active</span>
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <Play className="h-3 w-3" />
              <span className="hidden md:inline">Start AI</span>
            </>
          )}
        </button>
      </div>
    );
  }

  // BANNER VARIANT (For OverviewDashboard)
  return (
    <div className="w-full bg-panel rounded-xl border border-line p-3 sm:p-4 shadow-xs">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Left: AI Engine Info */}
        <div className="flex items-center gap-3">
          <div
            className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border ${
              isRunning
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-400'
            }`}
          >
            <Cpu className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-txt-primary">AI Autonomous Trading Engine</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider ${
                  isRunning
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                    : 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20'
                }`}
              >
                {isRunning && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />}
                {!isRunning && <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />}
                {aiState}
              </span>
              <span className="text-[11px] font-mono text-txt-muted hidden sm:inline">
                [{workspace} • {environment}]
              </span>
            </div>

            <p className="text-xs text-txt-secondary mt-0.5">
              {reason || (isRunning ? 'Autonomous quantitative order execution active' : 'AI order submission is paused')}
            </p>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={handleToggle}
            disabled={isLoading}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg border transition shadow-xs cursor-pointer ${
              isRunning
                ? 'bg-amber-500 text-white border-amber-600 hover:bg-amber-600'
                : 'bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700'
            }`}
          >
            {isLoading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : isRunning ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            <span>{isRunning ? 'Pause Auto-Trading' : 'Start Auto-Trading'}</span>
          </button>
        </div>
      </div>

      {/* Status Feedback Toast/Notification */}
      {message && (
        <div
          className={`mt-2.5 px-3 py-1.5 rounded-lg text-xs flex items-center justify-between border ${
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
    </div>
  );
}
