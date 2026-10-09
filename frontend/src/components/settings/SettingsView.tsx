'use client';

import React, { useState } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Settings, Shield, Lock, RefreshCw } from 'lucide-react';

export function SettingsView() {
  const { environment, workspace, account, envStatus, refreshData } = useTradingContext();
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [toggleMsg, setToggleMsg] = useState<string | null>(null);

  const handleToggleLiveTrading = async () => {
    const nextState = !envStatus?.live_trading_enabled_flag;
    const confirmText = nextState
      ? 'CAUTION: Are you sure you want to unlock LIVE order submission?'
      : 'Lock LIVE trading order submissions?';
    if (!confirm(confirmText)) return;

    try {
      setIsUpdating(true);
      setToggleMsg(null);
      const res = await api.toggleLiveTrading(nextState);
      setToggleMsg(res.message);
      await refreshData();
    } catch (err: any) {
      setToggleMsg(err?.message || 'Failed to toggle live trading gate');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Platform & Governance Settings
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Execution gates, environment controls, and venue connectivity.
        </p>
      </div>

      <div className="card-panel p-5 space-y-6">
        {/* Environment Authoritative Gate Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-line">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-brand" />
              <h3 className="text-sm font-bold text-txt-primary">
                Live Trading Authorization Gate
              </h3>
              <Badge variant={envStatus?.live_trading_enabled_flag ? 'live' : 'neutral'}>
                {envStatus?.live_trading_enabled_flag ? 'UNLOCKED (ACTIVE)' : 'LOCKED (OFF)'}
              </Badge>
            </div>
            <p className="text-xs text-txt-muted mt-1 max-w-xl">
              Controls whether live real-capital orders can be dispatched to Binance.
              Default is fail-closed (locked). Withdrawals remain strictly disabled.
            </p>
          </div>

          <button
            onClick={handleToggleLiveTrading}
            disabled={isUpdating}
            className={`px-4 py-2 text-xs font-bold rounded shadow-xs transition ${
              envStatus?.live_trading_enabled_flag
                ? 'bg-slate-900 text-white hover:bg-slate-800'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            {isUpdating
              ? 'Updating Gate...'
              : envStatus?.live_trading_enabled_flag
              ? 'Lock Live Trading'
              : 'Unlock Live Trading'}
          </button>
        </div>

        {toggleMsg && (
          <div className="p-3 bg-blue-50 border border-blue-200 text-blue-900 rounded text-xs">
            {toggleMsg}
          </div>
        )}

        {/* Account Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Active Account Identity</span>
            <span className="font-bold text-txt-primary block mt-1">{account?.account_id || 'N/A'}</span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Account Permissions</span>
            <span className="font-bold text-txt-primary block mt-1">
              {account?.permissions?.join(', ') || 'READ'}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Live Withdrawals Gate</span>
            <span className="font-bold text-loss block mt-1">PERMANENTLY LOCKED</span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Live Futures Capability</span>
            <span className="font-bold text-loss block mt-1">PERMANENTLY DISABLED</span>
          </div>
        </div>
      </div>
    </div>
  );
}
