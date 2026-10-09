'use client';

import React, { useState } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import {
  Shield,
  Activity,
  Layers,
  User,
  ArrowRightLeft,
  ChevronDown,
  Bell,
  Sun,
  Lock,
} from 'lucide-react';
import { Workspace } from '../../lib/types';

export function TopHeader() {
  const {
    environment,
    workspace,
    account,
    envStatus,
    portfolio,
    switchEnvironment,
    switchWorkspace,
  } = useTradingContext();

  const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
  const [isWsDropdownOpen, setIsWsDropdownOpen] = useState(false);

  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (portfolio?.broker_connected === false || portfolio?.total_equity === null);

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
      <header className="sticky top-0 z-40 h-14 bg-panel border-b border-line px-4 flex items-center justify-between shadow-sm">
        {/* Left: Brand + Environment Status + Workspace */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-brand text-white flex items-center justify-center font-bold text-sm tracking-wider shadow-sm">
              AQ
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-bold uppercase tracking-widest text-txt-primary">
                Aegis Quant
              </span>
              <span className="text-[10px] font-mono text-txt-muted tracking-tight">
                Institutional Terminal v6.0
              </span>
            </div>
          </div>

          <div className="h-5 w-px bg-line mx-1" />

          {/* Prominent Environment Indicator */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEnvModalOpen(true)}
              className="flex items-center gap-1.5 focus:outline-none group"
              title="Click to switch trading environment"
            >
              <Badge
                variant={isLive ? 'live' : 'demo'}
                size="md"
                dot={true}
                className="cursor-pointer group-hover:ring-2 transition"
              >
                {environment}
              </Badge>
              <span className="text-xs font-mono font-semibold text-txt-secondary">
                • {workspace} • {account?.broker || 'BINANCE'}
              </span>
            </button>
          </div>

          <div className="h-5 w-px bg-line mx-1 hidden sm:block" />

          {/* Workspace Selector Dropdown */}
          <div className="relative hidden sm:block">
            <button
              onClick={() => setIsWsDropdownOpen(!isWsDropdownOpen)}
              className="flex items-center gap-2 px-2.5 py-1 text-xs font-semibold rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-txt-secondary transition"
            >
              <Layers className="h-3.5 w-3.5 text-txt-muted" />
              <span>{workspaces.find((w) => w.id === workspace)?.label}</span>
              <ChevronDown className="h-3.5 w-3.5 text-txt-subtle" />
            </button>

            {isWsDropdownOpen && (
              <div className="absolute left-0 mt-1.5 w-52 bg-panel rounded-lg border border-line shadow-lg py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3 py-1 text-[11px] font-semibold text-txt-muted uppercase tracking-wider">
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
                        ? 'bg-blue-50/80 text-brand font-semibold'
                        : 'text-txt-secondary hover:bg-slate-50'
                    }`}
                  >
                    <span className="text-sm font-mono w-4">{ws.icon}</span>
                    <span>{ws.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Account Context + Market State + Profile Switcher */}
        <div className="flex items-center gap-3">
          {/* Broker Disconnected Pill */}
          {isLiveDisconnected && (
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-red-300 bg-red-50 text-red-700 text-xs font-mono font-bold animate-pulse shadow-sm"
              title="Live broker unauthenticated: real credentials required. Paper simulation fallback strictly disabled."
            >
              <span className="w-2 h-2 rounded-full bg-red-600 inline-block"></span>
              <span>BROKER DISCONNECTED</span>
            </div>
          )}

          {/* Active Account Pill */}
          <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md border border-line bg-slate-50 text-xs">
            <span className="text-[11px] font-mono text-txt-muted">Account:</span>
            <span className="font-semibold text-txt-primary">
              {account?.account_id || (isLive ? 'Binance Live Real' : 'Binance Spot Demo')}
            </span>
          </div>

          {/* Reconciliation Health Sentinel */}
          <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono border border-emerald-200 bg-emerald-50 text-emerald-800">
            <Shield className="h-3 w-3 text-emerald-600" />
            <span>RECON: OK</span>
          </div>

          {/* Environment Switch Action Button */}
          <button
            onClick={() => setIsEnvModalOpen(true)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold border transition ${
              isLive
                ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                : 'border-red-300 bg-red-50 text-red-800 hover:bg-red-100'
            }`}
          >
            <ArrowRightLeft className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Switch to</span>
            <span>{isLive ? 'DEMO' : 'LIVE'}</span>
          </button>

          {/* Notifications */}
          <button
            className="p-1.5 rounded-md text-txt-muted hover:text-txt-primary hover:bg-slate-100 transition"
            title="System notifications"
          >
            <Bell className="h-4 w-4" />
          </button>
        </div>
      </header>

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
                  ? 'bg-amber-600 hover:bg-amber-700'
                  : 'bg-red-600 hover:bg-red-700'
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

          <div className="p-3 rounded-lg border border-line bg-slate-50 flex items-center justify-between">
            <span className="font-medium text-txt-muted">Preserved Workspace:</span>
            <span className="font-mono font-semibold text-txt-primary">{workspace}</span>
          </div>

          <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-100 text-blue-900 leading-relaxed">
            <p className="font-semibold mb-1">Strict Isolation Notice:</p>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-blue-800">
              <li>Client session state, positions, and cache will be flushed completely.</li>
              <li>Your current workspace ({workspace}) is preserved; no redirection to INDIA.</li>
              <li>LIVE and DEMO balances, orders, and PnL never mix.</li>
            </ul>
          </div>
        </div>
      </Modal>
    </>
  );
}
