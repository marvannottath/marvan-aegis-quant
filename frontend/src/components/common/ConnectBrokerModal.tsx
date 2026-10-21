'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from './Badge';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Server,
  Lock,
  KeyRound,
  ExternalLink,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react';

interface ConnectBrokerModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCategory?: 'ALL' | 'CRYPTO' | 'INDIA' | 'FOREX_GOLD';
}

const DEFAULT_BROKERS = [
  {
    id: "binance_live",
    name: "Binance Live (Spot & Futures)",
    venue: "CRYPTO",
    category: "CRYPTO",
    environment: "LIVE",
    icon: "fa-solid fa-coins text-amber-400",
    badge_color: "amber",
    status: "STANDBY",
    balance: 0.0,
    currency: "USDT",
    description: "High-Speed Binance VIP API (Spot & USDⓈ-M Futures) with Read & Trade permissions only",
    fields: [
      { id: "api_key", label: "Binance API Key", type: "text", placeholder: "Paste Binance Live API Key", required: true },
      { id: "secret_key", label: "Binance API Secret", type: "password", placeholder: "Paste Binance Live Secret Key", required: true },
    ],
  },
  {
    id: "okx_live",
    name: "OKX V5 Institutional API",
    venue: "CRYPTO",
    category: "CRYPTO",
    environment: "LIVE",
    icon: "fa-solid fa-cube text-blue-400",
    badge_color: "blue",
    status: "STANDBY",
    balance: 0.0,
    currency: "USDT",
    description: "Institutional Multi-Currency Portfolio Margin & Web3 Order Execution",
    fields: [
      { id: "api_key", label: "OKX API Key", type: "text", placeholder: "Paste OKX API Key", required: true },
      { id: "secret_key", label: "OKX Secret Key", type: "password", placeholder: "Paste OKX Secret Key", required: true },
    ],
  },
  {
    id: "bybit_live",
    name: "Bybit Unified V5 API",
    venue: "CRYPTO",
    category: "CRYPTO",
    environment: "LIVE",
    icon: "fa-solid fa-bolt text-yellow-400",
    badge_color: "yellow",
    status: "STANDBY",
    balance: 0.0,
    currency: "USDT",
    description: "Bybit Unified Trading Account (UTA) for Crypto Perpetuals, Inverse Contracts & Spot",
    fields: [
      { id: "api_key", label: "Bybit API Key", type: "text", placeholder: "Paste Bybit V5 API Key", required: true },
      { id: "secret_key", label: "Bybit API Secret", type: "password", placeholder: "Paste Bybit V5 Secret Key", required: true },
    ],
  },
  {
    id: "binance_demo",
    name: "Binance Testnet Sandbox",
    venue: "CRYPTO",
    category: "CRYPTO",
    environment: "DEMO",
    icon: "fa-solid fa-coins text-amber-400",
    badge_color: "amber",
    status: "STANDBY",
    balance: 10000.0,
    currency: "USDT",
    description: "Binance Official Testnet SPOT environment for simulated algorithmic validation",
    fields: [
      { id: "api_key", label: "Testnet API Key", type: "text", placeholder: "Enter Binance Testnet API Key", required: true },
      { id: "secret_key", label: "Testnet Secret Key", type: "password", placeholder: "Enter Binance Testnet Secret Key", required: true },
    ],
  },
  {
    id: "kotak_neo_live",
    name: "Kotak Neo (Kotak Securities)",
    venue: "INDIA",
    category: "INDIA",
    environment: "LIVE",
    icon: "fa-solid fa-building-columns text-red-500",
    badge_color: "red",
    status: "STANDBY",
    balance: 0.0,
    currency: "INR",
    description: "Kotak Neo Open API (v2) for NSE & BSE Equities, F&O and Currency with zero intraday brokerage",
    fields: [
      { id: "consumer_key", label: "Kotak Consumer Key (API Key)", type: "text", placeholder: "Enter Kotak Neo Consumer Key", required: true },
      { id: "mobile_number", label: "Registered Mobile Number (10 digits without +91)", type: "text", placeholder: "e.g. 9207802002 (without +91)", required: true },
      { id: "ucc", label: "Client Code / UCC", type: "text", placeholder: "e.g. 16MT6", required: true },
      { id: "mpin", label: "Kotak Neo 6-digit MPIN", type: "password", placeholder: "Enter your 6-digit MPIN", required: true },
      { id: "totp", label: "Current 6-Digit TOTP (from Authenticator App)", type: "text", placeholder: "e.g. 582910 (Refreshes every 30s)", required: false },
      { id: "totp_secret", label: "OR TOTP Secret Key (base32 key for permanent daily auto-auth)", type: "password", placeholder: "Paste base32 secret (Optional)", required: false },
    ],
  },
  {
    id: "kotak_neo_demo",
    name: "Kotak Neo Sandbox (Paper)",
    venue: "INDIA",
    category: "INDIA",
    environment: "DEMO",
    icon: "fa-solid fa-flask text-red-400",
    badge_color: "red",
    status: "STANDBY",
    balance: 100000.0,
    currency: "INR",
    description: "Kotak Neo Sandbox simulator for testing NSE/BSE algos with zero financial risk",
    fields: [
      { id: "consumer_key", label: "Sandbox Consumer Key", type: "text", placeholder: "Enter Kotak Neo Sandbox Key", required: true },
      { id: "consumer_secret", label: "Sandbox Consumer Secret", type: "password", placeholder: "Enter Kotak Neo Sandbox Secret", required: true },
    ],
  },
  {
    id: "upstox_live",
    name: "Upstox Interactive (NSE/BSE)",
    venue: "INDIA",
    category: "INDIA",
    environment: "LIVE",
    icon: "fa-solid fa-arrow-trend-up text-purple-500",
    badge_color: "purple",
    status: "STANDBY",
    balance: 0.0,
    currency: "INR",
    description: "Upstox OpenAPI v2 with direct HFT order routing",
    fields: [
      { id: "api_key", label: "Upstox API Key", type: "text", placeholder: "Enter Upstox API Key", required: true },
      { id: "api_secret", label: "Upstox API Secret", type: "password", placeholder: "Enter Upstox API Secret", required: true },
    ],
  },
  {
    id: "zerodha_live",
    name: "Zerodha Kite Connect v3",
    venue: "INDIA",
    category: "INDIA",
    environment: "LIVE",
    icon: "fa-solid fa-paper-plane text-orange-400",
    badge_color: "orange",
    status: "STANDBY",
    balance: 0.0,
    currency: "INR",
    description: "Direct Kite Connect API for NSE Stocks, NIFTY/BANKNIFTY Options",
    fields: [
      { id: "api_key", label: "Kite API Key", type: "text", placeholder: "Enter Kite Connect API Key", required: true },
      { id: "api_secret", label: "Kite API Secret", type: "password", placeholder: "Enter Kite Connect API Secret", required: true },
    ],
  },
  {
    id: "mt5_live",
    name: "MetaTrader 5 (MT5 Direct)",
    venue: "FOREX_GOLD",
    category: "FOREX_GOLD",
    environment: "LIVE",
    icon: "fa-solid fa-chart-line text-emerald-500",
    badge_color: "emerald",
    status: "STANDBY",
    balance: 0.0,
    currency: "USD",
    description: "Institutional MT5 Direct STP Gateway for XAUUSD, Forex Majors, and Indices",
    fields: [
      { id: "login", label: "MT5 Login Account ID", type: "number", placeholder: "e.g. 12948271", required: true },
      { id: "password", label: "MT5 Trading Password", type: "password", placeholder: "Enter MT5 Master Password", required: true },
      { id: "server", label: "Broker Server Name", type: "text", placeholder: "e.g. Exness-Real19", required: true },
    ],
  },
];

export function ConnectBrokerModal({
  isOpen,
  onClose,
  defaultCategory = 'ALL',
}: ConnectBrokerModalProps) {
  const { environment, workspace, refreshData } = useTradingContext();
  const [brokers, setBrokers] = useState<any[]>(DEFAULT_BROKERS);
  const [selectedCategory, setSelectedCategory] = useState<string>(
    defaultCategory === 'ALL'
      ? workspace === 'INDIA'
        ? 'INDIA'
        : workspace === 'FOREX_GOLD'
        ? 'FOREX_GOLD'
        : 'CRYPTO'
      : defaultCategory
  );
  const [selectedBroker, setSelectedBroker] = useState<any | null>(null);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [showFullCreds, setShowFullCreds] = useState<boolean>(false);
  const [dailyTotpInput, setDailyTotpInput] = useState<string>('');
  const [isDailyTotpSubmitting, setIsDailyTotpSubmitting] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);
  const [saveResult, setSaveResult] = useState<{ status: string; message: string } | null>(null);

  const loadBrokers = async () => {
    try {
      setIsLoading(true);
      const list = await api.getAllBrokers();
      if (Array.isArray(list) && list.length > 0) {
        setBrokers(list);
      } else {
        setBrokers(DEFAULT_BROKERS);
      }
    } catch (err) {
      console.warn('Backend broker list fetch notice, using robust defaults:', err);
      setBrokers(DEFAULT_BROKERS);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadBrokers();
      setTestResult(null);
      setSaveResult(null);
    }
  }, [isOpen]);

  const categories = [
    { id: 'CONNECTED', label: '🟢 Connected Accounts' },
    { id: 'ALL', label: 'All Gateways' },
    { id: 'FOREX_GOLD', label: '🌍 Forex & Gold (MT5 & cTrader)' },
    { id: 'CRYPTO', label: '🪙 Crypto (Binance)' },
    { id: 'INDIA', label: '🇮🇳 India (Kotak Neo, Upstox, Zerodha)' },
  ];

  const [envFilter, setEnvFilter] = useState<'ALL' | 'LIVE' | 'DEMO'>('ALL');

  // Filter venues by category and optional environment filter (defaults to ALL so venues are never hidden)
  const filteredBrokers = (brokers && brokers.length > 0 ? brokers : DEFAULT_BROKERS).filter((b) => {
    if (!b) return false;
    if (envFilter !== 'ALL') {
      if (b.environment && b.environment !== envFilter) return false;
    }

    if (selectedCategory === 'CONNECTED') {
      return b.status === 'CONNECTED' || b.status === 'ONLINE' || b.status === 'ACTIVE' || b.is_active;
    }
    if (selectedCategory === 'ALL') return true;
    return b.category === selectedCategory || b.venue === selectedCategory;
  });

  const handleSelectBroker = (broker: any) => {
    if (!broker) return;
    setSelectedBroker(broker);
    setTestResult(null);
    setSaveResult(null);
    setShowFullCreds(false);
    setDailyTotpInput('');
    // Pre-populate defaults
    const initial: Record<string, any> = {
      broker_id: broker.id,
      environment: broker.environment || environment,
    };
    (broker.fields || []).forEach((f: any) => {
      initial[f.id] = '';
    });
    if (broker.id === 'kotak_neo_live') {
      if (broker.saved_ucc) initial.ucc = broker.saved_ucc;
      if (broker.saved_mobile) initial.mobile_number = broker.saved_mobile;
    }
    setFormValues(initial);
  };

  // Auto-select preferred broker (active > online/connected > first) when venues change or modal opens
  useEffect(() => {
    if (isOpen && filteredBrokers.length > 0) {
      const currentSelectedExists = selectedBroker && filteredBrokers.some((b) => b.id === selectedBroker.id);
      if (!currentSelectedExists) {
        const preferred =
          filteredBrokers.find((b) => b.is_active) ||
          filteredBrokers.find((b) => b.status === 'ONLINE' || b.status === 'CONNECTED') ||
          filteredBrokers[0];
        handleSelectBroker(preferred);
      }
    }
  }, [isOpen, brokers, selectedCategory, environment]);

  const handleInputChange = (fieldId: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [fieldId]: value }));
  };

  const handleTestConnection = async () => {
    if (!selectedBroker) return;
    try {
      setIsTesting(true);
      setTestResult(null);
      const res = await api.testBrokerConnection({
        broker_id: selectedBroker.id,
        ...formValues,
      });
      setTestResult({
        status: res.status || (res.success ? 'SUCCESS' : 'ERROR'),
        message: res.message || (res.status === 'SUCCESS' ? 'Handshake probe successful!' : 'Connection test failed'),
      });
    } catch (err: any) {
      setTestResult({
        status: 'ERROR',
        message: err?.message || 'Authentication error during handshake probe',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBroker) return;
    try {
      setIsSaving(true);
      setSaveResult(null);
      const payloadToSend: Record<string, any> = {
        broker_id: selectedBroker.id,
        ...formValues,
      };
      if (selectedBroker.id === 'kotak_neo_live' && dailyTotpInput) {
        payloadToSend.totp = dailyTotpInput;
      }
      const res = await api.connectBroker(payloadToSend);

      if (res.status === 'SUCCESS' || res.status === 'READY') {
        setSaveResult({
          status: 'SUCCESS',
          message: res.message || `${selectedBroker.name} authenticated and connected successfully!`,
        });
        await loadBrokers();
        await refreshData();
      } else {
        setSaveResult({
          status: 'ERROR',
          message: res.message || 'Server rejected broker credentials',
        });
      }
    } catch (err: any) {
      setSaveResult({
        status: 'ERROR',
        message: err?.message || 'Failed to save broker credentials',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleQuickDailyTotpSubmit = async () => {
    if (!dailyTotpInput || dailyTotpInput.length !== 6) return;
    try {
      setIsDailyTotpSubmitting(true);
      setSaveResult(null);
      const res = await api.connectBroker({
        broker_id: 'kotak_neo_live',
        totp: dailyTotpInput,
      });

      if (res.status === 'SUCCESS' || res.connected) {
        setSaveResult({
          status: 'SUCCESS',
          message: res.message || '✅ Kotak Neo Live Authenticated! Real session active.',
        });
        setDailyTotpInput('');
        await loadBrokers();
        await refreshData();
      } else {
        setSaveResult({
          status: 'ERROR',
          message: res.message || 'Kotak Neo authentication failed. Please check TOTP.',
        });
      }
    } catch (err: any) {
      setSaveResult({
        status: 'ERROR',
        message: err?.message || 'Authentication error during TOTP handshake',
      });
    } finally {
      setIsDailyTotpSubmitting(false);
    }
  };

  const handleDisconnect = async (brokerId: string) => {
    if (!confirm('Disconnect and remove stored credentials for this broker?')) return;
    try {
      await api.disconnectBroker(brokerId);
      await loadBrokers();
      await refreshData();
      if (selectedBroker?.id === brokerId) {
        setSelectedBroker(null);
      }
    } catch (err: any) {
      alert(`Disconnect failed: ${err?.message}`);
    }
  };

  const handleSwitchActiveBroker = async (broker: any) => {
    if (!broker) return;
    try {
      setIsSaving(true);
      setSaveResult(null);
      const poolMap: Record<string, string> = {
        binance_demo: 'BINANCE_TESTNET_DEMO',
        binance_live: 'BINANCE_LIVE_REAL',
        aegis_demo: 'AEGIS_QUANT_MASTER',
        mt5_demo: 'MT5_DEMO',
        mt5_live: 'MT5_LIVE_REAL',
        ctrader_live: 'CTRADER_LIVE',
        ctrader_demo: 'CTRADER_DEMO',
        kotak_neo_demo: 'KOTAK_NEO_DEMO_POOL',
        kotak_neo_live: 'KOTAK_NEO_LIVE_POOL',
        upstox_demo: 'UPSTOX_DEMO',
        upstox_live: 'UPSTOX_LIVE',
        zerodha_live: 'ZERODHA_LIVE_POOL',
      };
      const pool = poolMap[broker.id] || broker.pool_id || broker.id;
      const res = await fetch('/api/switch-trading-pool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pool,
          workspace: broker.venue || workspace,
          confirm_live_authorization: environment === 'LIVE',
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        if (typeof window !== 'undefined') {
          localStorage.setItem(`aq_active_broker_${environment}`, broker.id);
        }
        setSaveResult({
          status: 'SUCCESS',
          message: `Active Broker switched to ${broker.name}! Balances & positions updated for ${environment}.`,
        });
        await loadBrokers();
        if (refreshData) {
          try {
            await refreshData();
          } catch (e) {
            console.error('refreshData notice:', e);
          }
        }
      } else {
        setSaveResult({
          status: 'ERROR',
          message: data.message || 'Server rejected broker switch',
        });
      }
    } catch (err: any) {
      setSaveResult({
        status: 'ERROR',
        message: err.message || 'Failed to switch active broker',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl border border-line flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-line bg-slate-50">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${environment === 'LIVE' ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'}`}>
              <Server className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-txt-primary">
                  Institutional Broker Gateway Matrix
                </h2>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                  environment === 'LIVE'
                    ? 'bg-rose-100 text-rose-800 border border-rose-200'
                    : 'bg-blue-100 text-blue-800 border border-blue-200'
                }`}>
                  {environment === 'LIVE' ? '🔴 LIVE REAL CAPITAL' : '🧪 DEMO & SANDBOX'}
                </span>
              </div>
              <p className="text-xs text-txt-muted">
                {environment === 'LIVE'
                  ? 'Connect production API keys for Binance Live, Kotak Neo, Upstox, Zerodha, or MT5 STP. Testnet venues are strictly excluded.'
                  : 'Connect paper simulation and sandbox API keys for Binance Testnet, Kotak Neo Sandbox, Upstox Paper, or MT5 Demo.'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-200 rounded-md transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Category & Environment Tabs */}
        <div className="flex items-center justify-between px-6 py-2 border-b border-line bg-white overflow-x-auto gap-4">
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => {
                  setSelectedCategory(cat.id);
                  setTestResult(null);
                  setSaveResult(null);
                }}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition whitespace-nowrap cursor-pointer ${
                  selectedCategory === cat.id
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-txt-secondary hover:bg-slate-100'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg shrink-0">
            <button
              onClick={() => setEnvFilter('ALL')}
              className={`px-2.5 py-1 text-[11px] font-bold rounded-md transition cursor-pointer ${
                envFilter === 'ALL' ? 'bg-white shadow-xs text-slate-900' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setEnvFilter('LIVE')}
              className={`px-2.5 py-1 text-[11px] font-bold rounded-md transition cursor-pointer ${
                envFilter === 'LIVE' ? 'bg-rose-50 text-rose-700 font-extrabold shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              🔴 Live
            </button>
            <button
              onClick={() => setEnvFilter('DEMO')}
              className={`px-2.5 py-1 text-[11px] font-bold rounded-md transition cursor-pointer ${
                envFilter === 'DEMO' ? 'bg-blue-50 text-blue-700 font-extrabold shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              🧪 Demo
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Broker List Sidebar */}
            <div className="md:col-span-5 space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
              <div className="text-[11px] font-bold uppercase tracking-wider text-txt-muted mb-2">
                Supported Venues ({filteredBrokers.length})
              </div>
              {isLoading ? (
                <div className="py-12 text-center text-txt-muted text-xs">
                  <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-brand" />
                  Loading institutional brokers...
                </div>
              ) : filteredBrokers.length === 0 ? (
                <div className="py-8 text-center text-txt-muted text-xs">
                  No brokers available in this category.
                </div>
              ) : (
                filteredBrokers.map((b) => {
                  const isSelected = selectedBroker?.id === b.id;
                  const isConnected = b.status === 'CONNECTED' || b.status === 'ACTIVE' || b.status === 'ONLINE';

                  return (
                    <div
                      key={b.id}
                      onClick={() => handleSelectBroker(b)}
                      className={`p-3 rounded-lg border transition cursor-pointer flex flex-col gap-2 ${
                        isSelected
                          ? 'border-brand bg-blue-50/50 shadow-xs ring-1 ring-brand'
                          : 'border-line hover:border-slate-300 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-bold text-txt-primary">{b.name}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-wider ${
                              b.environment === 'LIVE' ? 'bg-rose-100 text-rose-700 border border-rose-200' : 'bg-blue-100 text-blue-700 border border-blue-200'
                            }`}>
                              {b.environment === 'LIVE' ? 'LIVE' : 'DEMO'}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-txt-muted block">
                            Balance: {typeof b.balance === 'number' ? b.balance.toLocaleString('en-US', { minimumFractionDigits: 2 }) : (b.balance || '0.00')} {b.currency || 'USD'}
                          </span>
                        </div>
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            isConnected
                              ? 'bg-emerald-50 text-profit border border-emerald-200'
                              : 'bg-slate-100 text-txt-muted border border-slate-200'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isConnected ? 'bg-profit animate-pulse' : 'bg-slate-400'
                            }`}
                          />
                          {b.status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-line/50">
                        <span className="text-[10px] text-txt-muted">{b.venue || b.category}</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSwitchActiveBroker(b);
                          }}
                          disabled={isSaving}
                          className={`px-2 py-1 rounded text-[10px] font-bold font-mono transition shadow-2xs cursor-pointer ${
                            isConnected
                              ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                              : 'bg-brand text-white hover:bg-blue-600'
                          }`}
                        >
                          {isConnected ? '✓ Active Broker' : '⚡ Activate Broker'}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Broker Configuration Form Panel */}
            <div className="md:col-span-7 bg-slate-50/60 rounded-xl border border-line p-5 flex flex-col justify-between">
              {selectedBroker ? (
                <form onSubmit={handleSaveConnection} className="space-y-4">
                  <div className="border-b border-line pb-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-txt-primary">
                        Configure {selectedBroker.name}
                      </h3>
                      <Badge variant={selectedBroker.environment === 'LIVE' ? 'live' : 'neutral'}>
                        {selectedBroker.environment} VENUE
                      </Badge>
                    </div>
                    <p className="text-xs text-txt-muted mt-1">
                      {selectedBroker.description}
                    </p>
                  </div>

                  {/* 1-Click Activate Broker Button */}
                  <div className="p-3 bg-blue-50/80 rounded-lg border border-blue-200 flex items-center justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold text-txt-primary block">{selectedBroker.name}</span>
                      <span className="text-[11px] font-mono text-txt-muted">
                        Live Balance: {typeof selectedBroker.balance === 'number' ? selectedBroker.balance.toLocaleString('en-US', { minimumFractionDigits: 2 }) : (selectedBroker.balance || '0.00')} {selectedBroker.currency || 'USD'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSwitchActiveBroker(selectedBroker)}
                      disabled={isSaving}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold font-mono transition shadow-xs cursor-pointer flex items-center gap-1"
                    >
                      <span>⚡ Set as Active Broker</span>
                    </button>
                  </div>

                  {/* Fast Daily TOTP Box for Kotak Neo */}
                  {selectedBroker.id === 'kotak_neo_live' && selectedBroker.has_stored_credentials && (
                    <div className="p-4 bg-gradient-to-br from-red-50/90 to-amber-50/70 rounded-xl border border-red-200/90 shadow-xs space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-red-600 text-white rounded-lg">
                            <KeyRound className="h-4 w-4" />
                          </div>
                          <div>
                            <h4 className="text-xs font-bold text-slate-900">
                              ⚡ Fast Daily TOTP Login
                            </h4>
                            <p className="text-[11px] text-slate-600">
                              UCC: <span className="font-mono font-bold text-slate-900">{selectedBroker.saved_ucc || selectedBroker.active_account_label || 'Configured'}</span> &bull; Mobile: <span className="font-mono text-slate-900">{selectedBroker.saved_mobile || 'Configured'}</span>
                            </p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                          selectedBroker.session_active_today
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : 'bg-amber-100 text-amber-900 border border-amber-300 animate-pulse'
                        }`}>
                          {selectedBroker.session_active_today ? '✓ SESSION ACTIVE TODAY' : '⚠️ DAILY 2FA REQUIRED'}
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold text-slate-800 flex items-center justify-between">
                          <span>Enter Today&apos;s 6-Digit TOTP (Authenticator App)</span>
                          <span className="text-[10px] text-slate-500 font-normal">Valid for 30s</span>
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            maxLength={6}
                            placeholder="e.g. 582910"
                            value={dailyTotpInput}
                            onChange={(e) => {
                              const val = e.target.value.replace(/\D/g, '');
                              setDailyTotpInput(val);
                              handleInputChange('totp', val);
                            }}
                            className="flex-1 px-3 py-2 text-sm font-mono font-bold tracking-widest text-center bg-white border border-red-300 rounded-lg focus:border-red-600 focus:ring-2 focus:ring-red-100 outline-none transition"
                          />
                          <button
                            type="button"
                            disabled={isDailyTotpSubmitting || dailyTotpInput.length !== 6}
                            onClick={handleQuickDailyTotpSubmit}
                            className="px-4 py-2 text-xs font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-xs transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5 shrink-0"
                          >
                            {isDailyTotpSubmitting ? (
                              <>
                                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                <span>Authenticating...</span>
                              </>
                            ) : (
                              <>
                                <span>🚀 Authenticate Session</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-red-200/60 flex items-center justify-between text-[11px]">
                        <span className="text-slate-600">
                          Credentials (API Key, Mobile, MPIN) are securely saved.
                        </span>
                        <button
                          type="button"
                          onClick={() => setShowFullCreds(!showFullCreds)}
                          className="font-bold text-red-700 hover:text-red-900 underline cursor-pointer"
                        >
                          {showFullCreds ? 'Hide Full Credentials' : 'Edit Full Credentials'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Form fields */}
                  {(!selectedBroker.has_stored_credentials || showFullCreds || selectedBroker.id !== 'kotak_neo_live') && (
                    <div className="space-y-3">
                      {(selectedBroker.fields || [
                        { id: 'api_key', label: 'API Key', type: 'text', placeholder: 'Enter API Key', required: true },
                        { id: 'secret_key', label: 'Secret Key', type: 'password', placeholder: 'Enter Secret Key', required: true },
                      ]).map((f: any) => (
                        <div key={f.id} className="space-y-1">
                          <label className="text-[11px] font-semibold text-txt-secondary flex items-center justify-between">
                            <span>{f.label}</span>
                            {f.required && !selectedBroker.has_stored_credentials && <span className="text-[10px] text-loss">*Required</span>}
                          </label>
                          <input
                            type={f.type || 'text'}
                            placeholder={f.placeholder}
                            required={f.required && !selectedBroker.has_stored_credentials}
                            value={formValues[f.id] || ''}
                            onChange={(e) => handleInputChange(f.id, e.target.value)}
                            className="w-full px-3 py-2 text-xs font-mono bg-white border border-line rounded-md focus:border-brand focus:ring-1 focus:ring-brand outline-none transition"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Binance Live Specific Checklist */}
                  {selectedBroker.id === 'binance_live' && (
                    <div className="p-3 bg-blue-50/90 rounded-lg border border-blue-200 text-blue-950 text-[11px] space-y-1.5">
                      <div className="font-bold flex items-center gap-1.5 text-blue-900">
                        <Shield className="h-3.5 w-3.5 text-blue-600" />
                        <span>Binance Live API Checklist:</span>
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-slate-700 pl-0.5">
                        <li>
                          <strong>IP Access Restriction:</strong> If your Binance key has IP restrictions enabled, whitelist Hostinger VPS IP:{' '}
                          <code className="bg-blue-100 text-blue-900 px-1.5 py-0.5 rounded font-mono font-bold select-all">187.127.189.139</code>
                        </li>
                        <li>
                          <strong>Permissions:</strong> In Binance API settings, check <em>Enable Reading</em> & <em>Enable Spot & Margin Trading</em>. (Withdrawals must remain OFF).
                        </li>
                        <li>
                          <strong>Key Expiration:</strong> Binance automatically expires unrestricted API keys after 90 days. If your key is older, create a new key on Binance.
                        </li>
                      </ul>
                    </div>
                  )}

                  {/* Zero-Trust Notice */}
                  <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-amber-900 text-[11px] flex items-start gap-2">
                    <Shield className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold block">Non-Custodial Zero-Trust Guard:</span>
                      <span>
                        Withdrawal permissions must remain strictly DISABLED on your broker key. Keys are sanitized and encrypted on server storage.
                      </span>
                    </div>
                  </div>

                  {/* Test Probe Result */}
                  {testResult && (
                    <div
                      className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
                        testResult.status === 'SUCCESS'
                          ? 'bg-emerald-50 text-profit border-emerald-200'
                          : 'bg-red-50 text-loss border-red-200'
                      }`}
                    >
                      {testResult.status === 'SUCCESS' ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                      )}
                      <span>{testResult.message}</span>
                    </div>
                  )}

                  {/* Save Result */}
                  {saveResult && (
                    <div
                      className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
                        saveResult.status === 'SUCCESS'
                          ? 'bg-emerald-50 text-profit border-emerald-200'
                          : 'bg-red-50 text-loss border-red-200'
                      }`}
                    >
                      {saveResult.status === 'SUCCESS' ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                      )}
                      <span>{saveResult.message}</span>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center justify-between pt-3 border-t border-line">
                    {selectedBroker.status === 'CONNECTED' ? (
                      <button
                        type="button"
                        onClick={() => handleDisconnect(selectedBroker.id)}
                        className="px-3 py-2 text-xs font-semibold text-loss hover:bg-red-50 rounded-md transition"
                      >
                        Disconnect Gateway
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleTestConnection}
                        disabled={isTesting}
                        className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border border-line bg-white hover:bg-slate-100 rounded-md text-txt-secondary transition"
                      >
                        <RefreshCw className={`h-3 w-3 ${isTesting ? 'animate-spin' : ''}`} />
                        <span>{isTesting ? 'Testing Handshake...' : 'Test Connection'}</span>
                      </button>
                    )}

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={onClose}
                        className="px-3 py-2 text-xs font-semibold text-txt-muted hover:bg-slate-200 rounded-md transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isSaving}
                        className="px-4 py-2 text-xs font-bold bg-slate-900 text-white hover:bg-slate-800 rounded-md shadow-xs transition disabled:opacity-50"
                      >
                        {isSaving ? 'Authenticating...' : 'Save & Authenticate'}
                      </button>
                    </div>
                  </div>
                </form>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 text-txt-muted space-y-3">
                  <div className="p-3 bg-white rounded-full border border-line shadow-2xs">
                    <KeyRound className="h-6 w-6 text-txt-subtle" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-txt-primary">
                      Select a Broker Venue
                    </h4>
                    <p className="text-xs text-txt-muted mt-1 max-w-sm">
                      Choose Binance for Crypto, Kotak Neo / Upstox for India Cash &amp; F&amp;O, or MetaTrader 5 for Gold &amp; Forex to configure and authenticate.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
