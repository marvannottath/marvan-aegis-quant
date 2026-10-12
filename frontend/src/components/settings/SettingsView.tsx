'use client';

import React, { useState } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Settings, Shield, Lock, AlertTriangle, KeyRound, Server, ExternalLink, ChevronRight } from 'lucide-react';
import { ConnectBrokerModal } from '../common/ConnectBrokerModal';

export function SettingsView() {
  const { environment, workspace, account, envStatus, refreshData } = useTradingContext();
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [toggleMsg, setToggleMsg] = useState<{ text: string; success: boolean } | null>(null);
  const [showTotpModal, setShowTotpModal] = useState<boolean>(false);
  const [isBrokerModalOpen, setIsBrokerModalOpen] = useState<boolean>(false);
  const [brokerModalCategory, setBrokerModalCategory] = useState<'ALL' | 'CRYPTO' | 'INDIA' | 'FOREX_GOLD'>('ALL');
  const [sessionToken, setSessionToken] = useState<string>('');
  const [totpCode, setTotpCode] = useState<string>('');

  const handleToggleLiveTrading = async () => {
    // If currently enabled, locking does not require step-up TOTP
    if (envStatus?.live_trading_enabled_flag) {
      if (!confirm('Lock LIVE trading order submissions immediately?')) return;
      try {
        setIsUpdating(true);
        setToggleMsg(null);
        const res = await api.toggleLiveTrading(false);
        setToggleMsg({ text: res.message, success: true });
        await refreshData();
      } catch (err: any) {
        setToggleMsg({ text: err?.message || 'Failed to lock live trading gate', success: false });
      } finally {
        setIsUpdating(false);
      }
    } else {
      // Unlocking requires step-up SUPER_ADMIN credentials + RFC 6238 TOTP code
      setShowTotpModal(true);
    }
  };

  const handleConfirmUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionToken.trim() || !totpCode.trim()) {
      setToggleMsg({ text: 'Both SUPER_ADMIN session token and 6-digit TOTP code are required.', success: false });
      return;
    }

    try {
      setIsUpdating(true);
      setToggleMsg(null);
      const res = await api.toggleLiveTrading(true, sessionToken.trim(), totpCode.trim());
      setToggleMsg({ text: res.message, success: true });
      setShowTotpModal(false);
      setSessionToken('');
      setTotpCode('');
      await refreshData();
    } catch (err: any) {
      setToggleMsg({ text: err?.message || 'Verification rejected by server-side Environment Gate', success: false });
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Platform Governance & Security Settings
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Authoritative execution gates, RFC 6238 TOTP anti-replay, and venue permissions.
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
              Controls whether live real-capital orders can be dispatched to exchange gateways.
              Default is fail-closed (locked). Unlocking requires SUPER_ADMIN credentials and RFC 6238 TOTP verification with anti-replay protection.
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
              ? 'Validating...'
              : envStatus?.live_trading_enabled_flag
              ? 'Lock Live Trading'
              : 'Unlock Live Trading (Requires TOTP)'}
          </button>
        </div>

        {/* Feedback message */}
        {toggleMsg && (
          <div
            className={`p-3 rounded text-xs flex items-center gap-2 ${
              toggleMsg.success
                ? 'bg-emerald-50 text-profit border border-emerald-200'
                : 'bg-red-50 text-loss border border-red-200'
            }`}
          >
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{toggleMsg.text}</span>
          </div>
        )}

        {/* Account Details & Perms */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Active Account Identity</span>
            <span className="font-bold text-txt-primary block mt-1">{account?.account_id || 'N/A'}</span>
            <span className="text-[10px] text-txt-subtle mt-0.5 block">{workspace} • {environment} Scope</span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Account Capabilities</span>
            <span className="font-bold text-txt-primary block mt-1">
              READ-ONLY AUDIT (Trading requires explicit gate unlock)
            </span>
            <span className="text-[10px] text-txt-subtle mt-0.5 block">Read permission does NOT grant order execution</span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Live Withdrawals Gate</span>
            <span className="font-bold text-loss block mt-1">PERMANENTLY LOCKED (FAIL-CLOSED)</span>
            <span className="text-[10px] text-txt-subtle mt-0.5 block">Zero-trust security policy enforced server-side</span>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Live Futures Capability</span>
            <span className="font-bold text-loss block mt-1">PERMANENTLY DISABLED</span>
            <span className="text-[10px] text-txt-subtle mt-0.5 block">Paper simulation only</span>
          </div>
        </div>
      </div>

      {/* Institutional Broker Gateway Matrix Card */}
      <div className="card-panel p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-brand rounded-lg border border-blue-100">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-txt-primary">
                Institutional Broker Gateways & Venue Integrations
              </h2>
              <p className="text-xs text-txt-muted mt-0.5">
                Connect and authenticate exchange APIs, Indian stock brokers, or MetaTrader 5 bridges with zero-trust storage.
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              setBrokerModalCategory('ALL');
              setIsBrokerModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-900 text-white hover:bg-slate-800 text-xs font-semibold shadow-xs transition"
          >
            <span>Open Broker Matrix</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* 3 Main Broker Cards by Workspace */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Crypto: Binance */}
          <div className="p-4 rounded-lg border border-line bg-slate-50/50 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-txt-primary">🪙 Binance Spot & Futures</span>
                <Badge variant={workspace === 'CRYPTO' ? 'info' : 'neutral'}>Crypto</Badge>
              </div>
              <p className="text-[11px] text-txt-muted mt-1">
                Direct HMAC-SHA256 authenticated REST/WebSocket execution for BTC, ETH, SOL, BNB.
              </p>
            </div>
            <button
              onClick={() => {
                setBrokerModalCategory('CRYPTO');
                setIsBrokerModalOpen(true);
              }}
              className="w-full py-1.5 px-2.5 text-xs font-semibold rounded border border-line bg-white hover:bg-slate-100 text-txt-secondary transition flex items-center justify-center gap-1"
            >
              <span>Configure Binance</span>
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          {/* India: Upstox & Zerodha */}
          <div className="p-4 rounded-lg border border-line bg-slate-50/50 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-txt-primary">🇮🇳 Upstox / Zerodha / Kotak</span>
                <Badge variant={workspace === 'INDIA' ? 'info' : 'neutral'}>India NSE</Badge>
              </div>
              <p className="text-[11px] text-txt-muted mt-1">
                OAuth2 / API Gateway for Indian Equities, NIFTY 50, and BSE derivatives execution.
              </p>
            </div>
            <button
              onClick={() => {
                setBrokerModalCategory('INDIA');
                setIsBrokerModalOpen(true);
              }}
              className="w-full py-1.5 px-2.5 text-xs font-semibold rounded border border-line bg-white hover:bg-slate-100 text-txt-secondary transition flex items-center justify-center gap-1"
            >
              <span>Configure Indian Broker</span>
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          {/* Forex & Gold: MetaTrader 5 */}
          <div className="p-4 rounded-lg border border-line bg-slate-50/50 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-txt-primary">🌍 Forex & Gold (cTrader / MT5)</span>
                <Badge variant={workspace === 'FOREX_GOLD' ? 'info' : 'neutral'}>Forex/Gold</Badge>
              </div>
              <p className="text-[11px] text-txt-muted mt-1">
                cTrader Open API & MT5 Direct Terminal execution for Spot Gold (XAUUSD) & Major Forex pairs.
              </p>
            </div>
            <button
              onClick={() => {
                setBrokerModalCategory('FOREX_GOLD');
                setIsBrokerModalOpen(true);
              }}
              className="w-full py-1.5 px-2.5 text-xs font-semibold rounded border border-line bg-white hover:bg-slate-100 text-txt-secondary transition flex items-center justify-center gap-1"
            >
              <span>Configure cTrader & MT5</span>
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Connect Broker Modal */}
      <ConnectBrokerModal
        isOpen={isBrokerModalOpen}
        onClose={() => setIsBrokerModalOpen(false)}
        defaultCategory={brokerModalCategory}
      />

      {/* TOTP Step-Up Modal */}
      {showTotpModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-panel border border-line rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-50 text-amber-600 rounded-lg border border-amber-200">
                <KeyRound className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-txt-primary">
                  SUPER_ADMIN Step-Up Authentication
                </h3>
                <p className="text-xs text-txt-muted">
                  RFC 6238 TOTP Anti-Replay Verification
                </p>
              </div>
            </div>

            <p className="text-xs text-txt-secondary leading-relaxed">
              Unlocking LIVE real-capital execution requires step-up verification. The server-side SQLite store verifies that the 6-digit TOTP code has never been used before and falls within the ±30-second time drift window.
            </p>

            <form onSubmit={handleConfirmUnlock} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                  Session Token (Bearer)
                </label>
                <input
                  type="password"
                  value={sessionToken}
                  onChange={(e) => setSessionToken(e.target.value)}
                  placeholder="Enter SUPER_ADMIN session token"
                  className="w-full px-3 py-2 rounded border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand text-xs font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                  6-Digit Authenticator TOTP Code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="000000"
                  className="w-full px-3 py-2 rounded border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand text-xs font-mono tracking-widest text-center text-base"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTotpModal(false)}
                  className="px-3 py-1.5 rounded border border-line bg-slate-50 text-txt-secondary text-xs font-semibold hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-4 py-1.5 rounded bg-red-600 text-white text-xs font-bold hover:bg-red-700 transition disabled:opacity-50"
                >
                  {isUpdating ? 'Verifying...' : 'Verify & Unlock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
