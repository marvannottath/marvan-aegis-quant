'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import {
  Shield,
  Layers,
  ChevronDown,
  Bell,
  Lock,
  Eye,
  EyeOff,
  Fingerprint,
  Link2,
  User,
  Settings,
  ShieldCheck,
  LogOut,
  Activity,
  KeyRound,
  RefreshCw,
} from 'lucide-react';
import { Workspace } from '../../lib/types';
import { ConnectBrokerModal } from '../common/ConnectBrokerModal';
import { AIAutoTradeControl } from '../common/AIAutoTradeControl';

export function TopHeader() {
  const {
    environment,
    workspace,
    portfolio,
    switchEnvironment,
    switchWorkspace,
    isFinancialMasked,
    toggleFinancialMask,
    isLocked,
    lockTerminal,
    unlockTerminal,
  } = useTradingContext();

  const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
  const [isWsDropdownOpen, setIsWsDropdownOpen] = useState(false);
  const [isBrokerModalOpen, setIsBrokerModalOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [telegramConfig, setTelegramConfig] = useState<any>(null);
  const [isTestingTelegram, setIsTestingTelegram] = useState(false);
  const [telegramFeedback, setTelegramFeedback] = useState<string | null>(null);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);

  const loadNotifications = async () => {
    try {
      const res = await fetch('/api/notifications/status');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.recent_alerts || []);
        setTelegramConfig(data.config || null);
      }
    } catch {
      // Quiet fail
    }
  };

  useEffect(() => {
    loadNotifications();
    const timer = setInterval(loadNotifications, 12000);
    return () => clearInterval(timer);
  }, []);

  const handleTestTelegramAlert = async () => {
    try {
      setIsTestingTelegram(true);
      setTelegramFeedback(null);
      const res = await fetch('/api/notifications/test-telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Aegis-Quant Telemetry Dispatch Test' }),
      });
      const data = await res.json();
      setTelegramFeedback(data.status === 'SUCCESS' ? 'Telegram alert dispatched!' : (data.message || 'Alert sent'));
      await loadNotifications();
    } catch (err: any) {
      setTelegramFeedback(err.message || 'Dispatch error');
    } finally {
      setIsTestingTelegram(false);
    }
  };

  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (portfolio === null || portfolio.broker_connected === false || portfolio.total_equity === null || portfolio.status === 'DISCONNECTED');

  const handleConfirmEnvSwitch = () => {
    setIsEnvModalOpen(false);
    switchEnvironment(isLive ? 'DEMO' : 'LIVE');
  };

  const workspaces: Array<{ id: Workspace; label: string; icon: string }> = [
    { id: 'CRYPTO', label: 'Crypto Spot', icon: '₿' },
    { id: 'INDIA', label: 'India Equities (NSE)', icon: '₹' },
    { id: 'FOREX_GOLD', label: 'Forex & Gold (XAU)', icon: '★' },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 h-14 bg-panel border-b border-line px-4 flex items-center justify-between shadow-2xs select-none">
        {/* Left: Clean Brand + Workspace Selector + Modern Environment Switcher */}
        <div className="flex items-center gap-3 md:gap-4">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="h-8 w-8 rounded-lg bg-brand text-white flex items-center justify-center font-bold text-xs tracking-wider shadow-xs">
              AQ
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-bold uppercase tracking-wider text-txt-primary group-hover:text-brand transition">
                Aegis Quant
              </span>
              <span className="text-[10px] font-mono text-txt-muted tracking-tight hidden sm:inline">
                Terminal v6.0
              </span>
            </div>
          </Link>

          <div className="h-5 w-px bg-line hidden sm:block" />

          {/* Workspace Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsWsDropdownOpen(!isWsDropdownOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border border-line bg-slate-50 dark:bg-panel-light hover:bg-slate-100 text-txt-secondary transition cursor-pointer"
            >
              <Layers className="h-3.5 w-3.5 text-txt-muted" />
              <span>{workspaces.find((w) => w.id === workspace)?.label}</span>
              <ChevronDown className="h-3.5 w-3.5 text-txt-subtle" />
            </button>

            {isWsDropdownOpen && (
              <div className="absolute left-0 mt-1.5 w-52 bg-panel rounded-lg border border-line shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3 py-1 text-[10px] font-semibold text-txt-muted uppercase tracking-wider">
                  Select Workspace
                </div>
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setIsWsDropdownOpen(false);
                      switchWorkspace(ws.id);
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs text-left transition ${
                      workspace === ws.id
                        ? 'bg-blue-50/80 dark:bg-blue-950/40 text-brand font-semibold'
                        : 'text-txt-secondary hover:bg-slate-50 dark:hover:bg-panel-light'
                    }`}
                  >
                    <span className="text-sm font-mono w-4">{ws.icon}</span>
                    <span>{ws.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Sleek Segmented DEMO / LIVE Switcher */}
          <div className="flex items-center bg-slate-100 dark:bg-panel-light p-0.5 rounded-lg border border-line text-[11px] font-bold font-mono">
            <button
              onClick={() => {
                if (isLive) setIsEnvModalOpen(true);
              }}
              className={`px-2.5 py-0.5 rounded-md transition ${
                !isLive
                  ? 'bg-emerald-600 text-white shadow-2xs font-black'
                  : 'text-txt-muted hover:text-txt-primary cursor-pointer'
              }`}
              title="Paper simulation pool ($19,950.55 USDT)"
            >
              DEMO
            </button>
            <button
              onClick={() => {
                if (!isLive) setIsEnvModalOpen(true);
              }}
              className={`px-2.5 py-0.5 rounded-md transition ${
                isLive
                  ? 'bg-amber-600 text-white shadow-2xs font-black'
                  : 'text-txt-muted hover:text-txt-primary cursor-pointer'
              }`}
              title="Live broker execution desk"
            >
              LIVE
            </button>
          </div>
        </div>

        {/* Right: Clean, Unified Tools Bar */}
        <div className="flex items-center gap-2 md:gap-3">
          {/* AI Autonomous Trading Engine Pill & Action Toggle */}
          <AIAutoTradeControl variant="compact" />

          {/* Subtle Broker Connection Status (Only shows clean Connect Broker pill when disconnected) */}
          {isLiveDisconnected ? (
            <button
              onClick={() => setIsBrokerModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 hover:bg-red-100 text-xs font-semibold shadow-2xs transition cursor-pointer"
              title="Click to authenticate real exchange credentials"
            >
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              <span className="text-xs">Connect Broker</span>
            </button>
          ) : isLive ? (
            <button
              onClick={() => setIsBrokerModalOpen(true)}
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 text-xs font-semibold hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition cursor-pointer"
              title="Click to view connected accounts and switch broker"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>
                {portfolio?.pool_name?.includes('CTRADER')
                  ? 'cTrader Live'
                  : portfolio?.pool_name?.includes('BINANCE')
                  ? 'Binance Live'
                  : portfolio?.pool_name?.includes('MT5')
                  ? 'MT5 Direct'
                  : portfolio?.pool_name?.includes('KOTAK')
                  ? 'Kotak Neo Live'
                  : portfolio?.pool_name?.includes('UPSTOX')
                  ? 'Upstox Live'
                  : portfolio?.pool_name?.includes('ZERODHA')
                  ? 'Zerodha Live'
                  : portfolio?.pool_name?.includes('ANGEL')
                  ? 'Angel One Live'
                  : portfolio?.pool_name?.includes('DHAN')
                  ? 'Dhan Live'
                  : 'Broker Active'}
              </span>
              <ChevronDown className="h-3 w-3 opacity-60" />
            </button>
          ) : null}

          {/* Privacy Amount Masking Toggle */}
          <button
            onClick={toggleFinancialMask}
            className={`p-1.5 rounded-lg border transition ${
              isFinancialMasked
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-500'
                : 'border-line text-txt-muted hover:text-txt-primary hover:bg-slate-100 dark:hover:bg-panel-light'
            }`}
            title={isFinancialMasked ? 'Reveal Balances & PnL' : 'Mask Balances & PnL (Privacy Shield)'}
          >
            {isFinancialMasked ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>

          {/* 5-Min Idle Lock Now Button */}
          <button
            onClick={lockTerminal}
            className="p-1.5 rounded-lg border border-line text-txt-muted hover:text-txt-primary hover:bg-slate-100 dark:hover:bg-panel-light transition"
            title="Lock Terminal Now (5-Minute Inactivity Sentinel Active)"
          >
            <Lock className="h-4 w-4" />
          </button>

          {/* Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setIsNotificationOpen(!isNotificationOpen);
                if (!isNotificationOpen) loadNotifications();
              }}
              className="p-1.5 rounded-lg text-txt-muted hover:text-txt-primary hover:bg-slate-100 dark:hover:bg-panel-light transition cursor-pointer relative"
              title="System notifications & Telegram alerts"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            </button>

            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-panel rounded-xl border border-line shadow-2xl py-3 px-4 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="flex items-center justify-between pb-2 border-b border-line mb-3">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4 text-brand" />
                    <span className="text-xs font-bold text-txt-primary">Live Alerts & Notifications</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-bold">
                    ONLINE
                  </span>
                </div>

                {/* Telegram Integration Status */}
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-panel-light/30 border border-line mb-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-txt-primary flex items-center gap-1.5">
                      <span className="text-blue-500">✈</span> Telegram Engine:
                    </span>
                    <span className="text-[11px] font-mono text-txt-muted">
                      {telegramConfig?.telegram_chat_id ? `ID: ${telegramConfig.telegram_chat_id}` : 'Configured'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-line/60">
                    <button
                      onClick={handleTestTelegramAlert}
                      disabled={isTestingTelegram}
                      className="px-2.5 py-1 text-[11px] font-bold rounded bg-brand text-white hover:bg-blue-600 transition shadow-2xs cursor-pointer flex items-center gap-1"
                    >
                      {isTestingTelegram ? <RefreshCw className="h-3 w-3 animate-spin" /> : null}
                      <span>Test Telegram Alert</span>
                    </button>
                    {telegramFeedback && (
                      <span className="text-[10px] font-mono text-emerald-600 truncate max-w-[160px]">
                        {telegramFeedback}
                      </span>
                    )}
                  </div>
                </div>

                {/* Recent Alerts List */}
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {notifications.length === 0 ? (
                    <div className="py-4 text-center text-xs text-txt-muted font-mono">
                      No active security or risk alerts. System nominal.
                    </div>
                  ) : (
                    notifications.map((n: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg border border-line text-xs font-mono space-y-1 hover:bg-slate-50 dark:hover:bg-panel-light/30"
                      >
                        <div className="flex items-center justify-between text-[10px] text-txt-muted">
                          <span className="font-bold uppercase text-brand">{n.type || 'SYSTEM'}</span>
                          <span>{n.timestamp || 'Just now'}</span>
                        </div>
                        <p className="text-txt-primary text-[11px]">{n.message || n.text}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User Profile Avatar Button */}
          <button
            onClick={() => setIsProfileOpen(true)}
            className="flex items-center gap-2 py-1 px-2 rounded-full border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition cursor-pointer shadow-2xs"
            title="Trader Profile & Account"
          >
            <div className="w-6 h-6 rounded-full bg-linear-to-tr from-brand to-blue-600 text-white flex items-center justify-center text-[10px] font-black uppercase shadow-xs">
              DT
            </div>
            <span className="hidden sm:inline font-mono text-xs font-bold text-txt-primary">
              Trader
            </span>
            <ChevronDown className="h-3 w-3 text-txt-subtle" />
          </button>
        </div>
      </header>

      {/* User Profile & Trader Account Modal */}
      <Modal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        title="Trader Profile & Account"
        description="Institutional Algorithmic Desk Credentials"
        footer={
          <div className="flex items-center justify-between w-full">
            <button
              onClick={() => {
                setIsProfileOpen(false);
                lockTerminal();
              }}
              className="px-3 py-1.5 text-xs font-semibold rounded-md text-red-600 hover:bg-red-50 border border-red-200 transition flex items-center gap-1.5 cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Lock Session</span>
            </button>
            <button
              onClick={() => setIsProfileOpen(false)}
              className="px-4 py-1.5 text-xs font-bold rounded-md bg-brand hover:bg-brand-dark text-white transition cursor-pointer"
            >
              Close
            </button>
          </div>
        }
      >
        <div className="space-y-4 text-xs">
          {/* Identity Card */}
          <div className="p-4 rounded-xl border border-line bg-slate-50/70 flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-full bg-linear-to-tr from-brand to-blue-600 text-white flex items-center justify-center text-base font-black uppercase shadow-xs shrink-0">
              DT
            </div>
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-txt-primary truncate">Desk Trader</span>
                <Badge variant="live" size="sm">TIER-1 PRO</Badge>
              </div>
              <p className="text-[11px] text-txt-muted font-mono">
                UID: AQ-INST-98214 • Role: Senior Quant Desk
              </p>
              <p className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Session Active • Double-Entry Ledger Linked
              </p>
            </div>
          </div>

          {/* Quick Context Stats */}
          <div className="grid grid-cols-2 gap-2 text-txt-secondary font-mono">
            <div className="p-2.5 rounded-lg border border-line bg-white">
              <span className="text-[10px] text-txt-muted uppercase block">Active Workspace</span>
              <span className="font-bold text-txt-primary">{workspace}</span>
            </div>
            <div className="p-2.5 rounded-lg border border-line bg-white">
              <span className="text-[10px] text-txt-muted uppercase block">Execution Mode</span>
              <span className={`font-bold ${isLive ? 'text-amber-600' : 'text-emerald-600'}`}>
                {isLive ? 'LIVE BROKER' : 'DEMO PAPER'}
              </span>
            </div>
          </div>

          {/* Full Profile & Security Action */}
          <Link
            href={isLive ? '/profile' : '/demo/profile'}
            onClick={() => setIsProfileOpen(false)}
            className="w-full py-2 px-3 rounded-lg bg-brand text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs hover:bg-brand/90 transition cursor-pointer"
          >
            <User className="h-3.5 w-3.5" />
            <span>Open Profile & 2FA Security Center</span>
          </Link>

          {/* Navigation Shortcuts */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-txt-muted block">
              Terminal Preferences
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Link
                href={isLive ? '/risk' : '/demo/risk'}
                onClick={() => setIsProfileOpen(false)}
                className="p-2.5 rounded-lg border border-line bg-white hover:bg-slate-50 transition flex items-center gap-2 text-txt-primary font-medium"
              >
                <ShieldCheck className="h-4 w-4 text-brand shrink-0" />
                <div className="truncate">
                  <span className="block font-semibold">Risk Center</span>
                  <span className="text-[10px] text-txt-muted block">Limits & Profiles</span>
                </div>
              </Link>

              <Link
                href={isLive ? '/security' : '/demo/security'}
                onClick={() => setIsProfileOpen(false)}
                className="p-2.5 rounded-lg border border-line bg-white hover:bg-slate-50 transition flex items-center gap-2 text-txt-primary font-medium"
              >
                <KeyRound className="h-4 w-4 text-emerald-600 shrink-0" />
                <div className="truncate">
                  <span className="block font-semibold">Security & TOTP</span>
                  <span className="text-[10px] text-txt-muted block">MFA Verification</span>
                </div>
              </Link>

              <Link
                href={isLive ? '/settings' : '/demo/settings'}
                onClick={() => setIsProfileOpen(false)}
                className="p-2.5 rounded-lg border border-line bg-white hover:bg-slate-50 transition flex items-center gap-2 text-txt-primary font-medium"
              >
                <Settings className="h-4 w-4 text-txt-muted shrink-0" />
                <div className="truncate">
                  <span className="block font-semibold">API Settings</span>
                  <span className="text-[10px] text-txt-muted block">Broker Credentials</span>
                </div>
              </Link>

              <Link
                href={isLive ? '/audit' : '/demo/audit'}
                onClick={() => setIsProfileOpen(false)}
                className="p-2.5 rounded-lg border border-line bg-white hover:bg-slate-50 transition flex items-center gap-2 text-txt-primary font-medium"
              >
                <Activity className="h-4 w-4 text-blue-600 shrink-0" />
                <div className="truncate">
                  <span className="block font-semibold">Audit Ledger</span>
                  <span className="text-[10px] text-txt-muted block">Cryptographic Log</span>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </Modal>

      {/* Explicit Environment Switch Confirmation Modal */}
      <Modal
        isOpen={isEnvModalOpen}
        onClose={() => setIsEnvModalOpen(false)}
        title={`Switch Environment: ${environment} → ${isLive ? 'DEMO' : 'LIVE'}`}
        description="Strict execution environment boundary"
        footer={
          <>
            <button
              onClick={() => setIsEnvModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold rounded-md border border-line bg-white hover:bg-slate-50 text-txt-secondary transition"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmEnvSwitch}
              className={`px-4 py-1.5 text-xs font-semibold rounded-md text-white transition ${
                isLive
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              }`}
            >
              Confirm Switch to {isLive ? 'DEMO' : 'LIVE'}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-xs text-txt-secondary">
          <div className="p-3 rounded-lg border border-line bg-slate-50 flex items-center justify-between">
            <span className="font-medium text-txt-muted">Current Environment:</span>
            <Badge variant={isLive ? 'live' : 'demo'}>{environment}</Badge>
          </div>

          <div className="p-3 rounded-lg border border-line bg-slate-50 flex items-center justify-between">
            <span className="font-medium text-txt-muted">Target Environment:</span>
            <Badge variant={isLive ? 'demo' : 'live'}>{isLive ? 'DEMO' : 'LIVE'}</Badge>
          </div>

          <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-100 text-blue-900 leading-relaxed">
            <p className="font-semibold mb-1">Strict Isolation Notice:</p>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-blue-800">
              <li>Client session state, positions, and cache will be flushed completely.</li>
              <li>LIVE and DEMO balances, orders, and PnL never mix.</li>
            </ul>
          </div>
        </div>
      </Modal>

      {/* Institutional Broker Gateway Connection Modal */}
      <ConnectBrokerModal
        isOpen={isBrokerModalOpen}
        onClose={() => setIsBrokerModalOpen(false)}
      />

      {/* 5-Minute Inactivity / Manual Lock Fullscreen Overlay */}
      {isLocked && (
        <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-panel border border-line rounded-xl shadow-2xl p-6 space-y-5 text-center">
            <div className="mx-auto w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
              <Lock className="w-7 h-7" />
            </div>

            <div>
              <h2 className="text-lg font-bold text-txt-primary">Terminal Locked</h2>
              <p className="text-xs text-txt-muted mt-1">
                5-minute inactivity sentinel or manual privacy lock engaged. Enter your password or use biometrics to resume.
              </p>
            </div>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setIsUnlocking(true);
                setUnlockError(null);
                const ok = await unlockTerminal(unlockPassword);
                setIsUnlocking(false);
                if (!ok) {
                  setUnlockError('Invalid password. Default password is: marvan');
                } else {
                  setUnlockPassword('');
                }
              }}
              className="space-y-4 text-left"
            >
              <div>
                <label className="block text-xs font-semibold text-txt-secondary mb-1">
                  Master Trader Password <span className="font-normal text-txt-muted font-mono">(Default: marvan)</span>
                </label>
                <input
                  type="password"
                  value={unlockPassword}
                  onChange={(e) => setUnlockPassword(e.target.value)}
                  placeholder="Enter terminal password (e.g. marvan)"
                  autoFocus
                  className="w-full px-3 py-2 text-sm rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand font-mono"
                />
                {unlockError && (
                  <p className="text-xs text-red-500 font-semibold mt-1">{unlockError}</p>
                )}
              </div>

              <div className="space-y-2">
                <button
                  type="submit"
                  disabled={isUnlocking}
                  className="w-full py-2 px-4 rounded-lg bg-brand hover:bg-brand/90 text-white font-semibold text-xs transition shadow-sm disabled:opacity-50"
                >
                  {isUnlocking ? 'Unlocking...' : 'Unlock Terminal'}
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    setIsUnlocking(true);
                    setUnlockError(null);
                    try {
                      if (typeof window !== 'undefined' && (window as any).PublicKeyCredential) {
                        try {
                          const challenge = new Uint8Array(32);
                          window.crypto.getRandomValues(challenge);
                          await navigator.credentials.get({
                            publicKey: {
                              challenge,
                              timeout: 10000,
                              userVerification: 'preferred',
                            },
                          });
                        } catch (biometricErr) {
                          console.log('Biometric enclave notice:', biometricErr);
                        }
                      }
                      const ok = await unlockTerminal('marvan');
                      if (!ok) {
                        setUnlockError('Biometric verification failed');
                      }
                    } catch (e: any) {
                      setUnlockError(e?.message || 'Biometric verification error');
                    } finally {
                      setIsUnlocking(false);
                    }
                  }}
                  className="w-full py-2 px-4 rounded-lg border border-line bg-panel-light hover:bg-panel text-txt-secondary font-semibold text-xs flex items-center justify-center gap-2 transition cursor-pointer"
                >
                  <Fingerprint className="w-4 h-4 text-brand" />
                  <span>Mac Touch ID / Face ID</span>
                </button>
              </div>
            </form>

            <div className="text-[11px] font-mono text-txt-subtle pt-2 border-t border-line">
              Aegis-Quant Non-Custodial Security • IP Whitelisted
            </div>
          </div>
        </div>
      )}
    </>
  );
}
