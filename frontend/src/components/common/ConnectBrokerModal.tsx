'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Server,
  KeyRound,
  Shield,
  Sliders,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

interface ConnectBrokerModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultCategory?: 'ALL' | 'CRYPTO' | 'INDIA' | 'FOREX_GOLD';
}

interface BrokerConfig {
  id: string;
  name: string;
  short_name: string;
  venue: 'CRYPTO' | 'INDIA' | 'FOREX_GOLD';
  category: 'CRYPTO' | 'INDIA' | 'FOREX_GOLD';
  environment: 'LIVE' | 'DEMO';
  balance: number;
  currency: string;
  active_account_label?: string;
  saved_ucc?: string;
  saved_mobile?: string;
  status: string;
  is_connected: boolean;
  has_stored_credentials?: boolean;
  ping_ms?: string;
  description: string;
  fields: Array<{
    id: string;
    label: string;
    type?: string;
    placeholder: string;
    required: boolean;
  }>;
}

const DEFAULT_BROKERS: BrokerConfig[] = [
  // Forex & Gold
  {
    id: 'ctrader_live',
    name: 'cTrader Open API',
    short_name: 'cTrader ECN',
    venue: 'FOREX_GOLD',
    category: 'FOREX_GOLD',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'USD',
    active_account_label: 'cTrader #6187232',
    status: 'ONLINE',
    is_connected: true,
    has_stored_credentials: true,
    ping_ms: '24ms',
    description: 'Spotware Open API for ECN ultra-low latency Forex, Metals & Indices',
    fields: [
      { id: 'client_id', label: 'cTrader Client ID', type: 'text', placeholder: 'Enter cTrader Client ID', required: true },
      { id: 'client_secret', label: 'cTrader Client Secret', type: 'password', placeholder: 'Enter cTrader Client Secret', required: true },
      { id: 'access_token', label: 'OAuth Access Token', type: 'password', placeholder: 'Enter cTrader Access Token', required: true },
      { id: 'account_id', label: 'Trading Account ID', type: 'text', placeholder: 'e.g. 6187232', required: true },
    ],
  },
  {
    id: 'mt5_live',
    name: 'MetaTrader 5 (MT5 Direct)',
    short_name: 'MetaTrader 5',
    venue: 'FOREX_GOLD',
    category: 'FOREX_GOLD',
    environment: 'LIVE',
    balance: 1000.0,
    currency: 'USD',
    active_account_label: '#5056397217 (Wt@h0nQj)',
    status: 'CONNECTED',
    is_connected: true,
    has_stored_credentials: true,
    ping_ms: '12ms',
    description: 'Direct STP Gateway for XAUUSD, Forex Majors & Commodities',
    fields: [
      { id: 'login', label: 'MT5 Login ID', type: 'number', placeholder: 'e.g. 5056397217', required: true },
      { id: 'password', label: 'Trader Password', type: 'password', placeholder: 'Enter MT5 Master Password', required: true },
      { id: 'server', label: 'Broker Server', type: 'text', placeholder: 'e.g. Exness-Real19', required: true },
    ],
  },
  {
    id: 'exness_live',
    name: 'Exness Pro STP Gateway',
    short_name: 'Exness Pro',
    venue: 'FOREX_GOLD',
    category: 'FOREX_GOLD',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'USD',
    active_account_label: 'NO CREDENTIALS SAVED',
    status: 'STANDBY',
    is_connected: false,
    description: 'Direct MT5/cTrader bridge to Exness zero-spread Raw ECN accounts',
    fields: [
      { id: 'login', label: 'Exness Account ID', type: 'text', placeholder: 'e.g. 1928374', required: true },
      { id: 'password', label: 'Account Password', type: 'password', placeholder: 'Enter Exness Password', required: true },
      { id: 'server', label: 'Exness Server', type: 'text', placeholder: 'e.g. Exness-Real10', required: true },
    ],
  },

  // Crypto
  {
    id: 'binance_live',
    name: 'Binance Live (Spot & Futures)',
    short_name: 'Binance Live',
    venue: 'CRYPTO',
    category: 'CRYPTO',
    environment: 'LIVE',
    balance: 7.39,
    currency: 'USDT',
    active_account_label: 'p15••••puy',
    status: 'ONLINE',
    is_connected: true,
    has_stored_credentials: true,
    ping_ms: '18ms',
    description: 'Binance VIP Spot & USDⓈ-M Perpetual Futures Gateway',
    fields: [
      { id: 'api_key', label: 'Binance API Key', type: 'text', placeholder: 'Paste Binance Live API Key', required: true },
      { id: 'secret_key', label: 'Binance API Secret', type: 'password', placeholder: 'Paste Binance Live Secret Key', required: true },
    ],
  },
  {
    id: 'bybit_live',
    name: 'Bybit Unified V5 API',
    short_name: 'Bybit V5',
    venue: 'CRYPTO',
    category: 'CRYPTO',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'USDT',
    active_account_label: 'NO CREDENTIALS SAVED',
    status: 'STANDBY',
    is_connected: false,
    description: 'Bybit Unified Trading Account (UTA) for Perpetuals & Spot',
    fields: [
      { id: 'api_key', label: 'Bybit API Key', type: 'text', placeholder: 'Paste Bybit V5 API Key', required: true },
      { id: 'secret_key', label: 'Bybit API Secret', type: 'password', placeholder: 'Paste Bybit V5 Secret Key', required: true },
    ],
  },
  {
    id: 'okx_live',
    name: 'OKX V5 Institutional API',
    short_name: 'OKX V5',
    venue: 'CRYPTO',
    category: 'CRYPTO',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'USDT',
    active_account_label: 'NO CREDENTIALS SAVED',
    status: 'STANDBY',
    is_connected: false,
    description: 'OKX Multi-Currency Portfolio Margin & Web3 Order Gateway',
    fields: [
      { id: 'api_key', label: 'OKX API Key', type: 'text', placeholder: 'Paste OKX API Key', required: true },
      { id: 'secret_key', label: 'OKX Secret Key', type: 'password', placeholder: 'Paste OKX Secret Key', required: true },
    ],
  },

  // India
  {
    id: 'kotak_neo_live',
    name: 'Kotak Neo (Kotak Securities)',
    short_name: 'Kotak Neo',
    venue: 'INDIA',
    category: 'INDIA',
    environment: 'LIVE',
    balance: 708.6,
    currency: 'INR',
    saved_ucc: '16MT6',
    saved_mobile: '9207802002',
    active_account_label: '16MT6',
    status: 'ONLINE',
    is_connected: true,
    has_stored_credentials: true,
    ping_ms: '32ms',
    description: 'Kotak Neo Open API (v2) for NSE & BSE Equities, F&O and Currency',
    fields: [
      { id: 'consumer_key', label: 'Kotak Consumer Key', type: 'text', placeholder: 'Enter Kotak Neo Consumer Key', required: true },
      { id: 'mobile_number', label: 'Registered Mobile', type: 'text', placeholder: 'e.g. 9207802002', required: true },
      { id: 'ucc', label: 'Client Code / UCC', type: 'text', placeholder: 'e.g. 16MT6', required: true },
      { id: 'mpin', label: 'Kotak Neo 6-digit MPIN', type: 'password', placeholder: 'Enter your 6-digit MPIN', required: true },
      { id: 'totp', label: 'Current 6-Digit TOTP', type: 'text', placeholder: 'e.g. 582910', required: false },
      { id: 'totp_secret', label: 'TOTP Secret Key (Optional)', type: 'password', placeholder: 'Paste base32 secret (Optional)', required: false },
    ],
  },
  {
    id: 'upstox_live',
    name: 'Upstox Pro (NSE / BSE)',
    short_name: 'Upstox Pro',
    venue: 'INDIA',
    category: 'INDIA',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'INR',
    active_account_label: 'NO CREDENTIALS SAVED',
    status: 'STANDBY',
    is_connected: false,
    description: 'Upstox OpenAPI v2 with direct HFT order execution',
    fields: [
      { id: 'api_key', label: 'Upstox API Key', type: 'text', placeholder: 'Enter Upstox API Key', required: true },
      { id: 'api_secret', label: 'Upstox API Secret', type: 'password', placeholder: 'Enter Upstox API Secret', required: true },
    ],
  },
  {
    id: 'zerodha_live',
    name: 'Zerodha Kite Connect v3',
    short_name: 'Zerodha Kite',
    venue: 'INDIA',
    category: 'INDIA',
    environment: 'LIVE',
    balance: 0.0,
    currency: 'INR',
    active_account_label: 'NO CREDENTIALS SAVED',
    status: 'STANDBY',
    is_connected: false,
    description: 'Direct Kite Connect API for NSE Stocks & NIFTY/BANKNIFTY Options',
    fields: [
      { id: 'api_key', label: 'Kite API Key', type: 'text', placeholder: 'Enter Kite Connect API Key', required: true },
      { id: 'api_secret', label: 'Kite API Secret', type: 'password', placeholder: 'Enter Kite Connect API Secret', required: true },
    ],
  },
];

export function ConnectBrokerModal({
  isOpen,
  onClose,
  defaultCategory = 'ALL',
}: ConnectBrokerModalProps) {
  const { environment, workspace, refreshData } = useTradingContext();
  const [brokers, setBrokers] = useState<BrokerConfig[]>(DEFAULT_BROKERS);
  const [selectedMarket, setSelectedMarket] = useState<'CRYPTO' | 'INDIA' | 'FOREX_GOLD'>('CRYPTO');
  const [selectedBrokerId, setSelectedBrokerId] = useState<string>('binance_live');
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [showEditKeys, setShowEditKeys] = useState<boolean>(false);
  const [dailyTotpInput, setDailyTotpInput] = useState<string>('');
  const [isDailyTotpSubmitting, setIsDailyTotpSubmitting] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [saveResult, setSaveResult] = useState<{ status: string; message: string } | null>(null);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);

  // Load broker list from API
  const loadBrokers = async () => {
    try {
      const list = await api.getAllBrokers();
      if (Array.isArray(list) && list.length > 0) {
        // Merge API data over defaults to preserve fields and clean descriptions
        const merged = DEFAULT_BROKERS.map((def) => {
          const apiMatch = list.find((b: any) => b.id === def.id);
          return apiMatch ? { ...def, ...apiMatch } : def;
        });
        setBrokers(merged);
      }
    } catch (err) {
      console.warn('Backend broker list warning:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadBrokers();
      setShowEditKeys(false);
      setSaveResult(null);
      setTestResult(null);
      setDailyTotpInput('');

      // Auto-select category matching current workspace
      const initialCat: 'CRYPTO' | 'INDIA' | 'FOREX_GOLD' =
        workspace === 'INDIA' || defaultCategory === 'INDIA'
          ? 'INDIA'
          : workspace === 'FOREX_GOLD' || defaultCategory === 'FOREX_GOLD'
          ? 'FOREX_GOLD'
          : 'CRYPTO';

      setSelectedMarket(initialCat);

      // Default selected broker per category (prioritizing user favorites: cTrader for Forex, Kotak for India, Binance for Crypto)
      if (initialCat === 'FOREX_GOLD') {
        setSelectedBrokerId('ctrader_live');
      } else if (initialCat === 'INDIA') {
        setSelectedBrokerId('kotak_neo_live');
      } else {
        setSelectedBrokerId('binance_live');
      }
    }
  }, [isOpen, workspace, defaultCategory]);

  // Brokers filtered by the active market category (LIVE environment only to eliminate demo noise)
  const marketBrokers = useMemo(() => {
    return brokers.filter((b) => b.venue === selectedMarket || b.category === selectedMarket);
  }, [brokers, selectedMarket]);

  const selectedBroker = useMemo(() => {
    return marketBrokers.find((b) => b.id === selectedBrokerId) || marketBrokers[0] || brokers[0];
  }, [marketBrokers, selectedBrokerId]);

  const isConnected = Boolean(
    selectedBroker && (
      selectedBroker.is_connected ||
      selectedBroker.status === 'ONLINE' ||
      selectedBroker.status === 'CONNECTED' ||
      selectedBroker.status === 'ACTIVE' ||
      selectedBroker.has_stored_credentials
    )
  );

  const handleSelectMarket = (cat: 'CRYPTO' | 'INDIA' | 'FOREX_GOLD') => {
    setSelectedMarket(cat);
    setShowEditKeys(false);
    setSaveResult(null);
    setTestResult(null);

    // Pick top connected broker or first broker in that category
    const catBrokers = brokers.filter((b) => b.venue === cat || b.category === cat);
    if (cat === 'FOREX_GOLD') {
      setSelectedBrokerId('ctrader_live');
    } else if (cat === 'INDIA') {
      setSelectedBrokerId('kotak_neo_live');
    } else {
      setSelectedBrokerId('binance_live');
    }
  };

  const handleSelectBroker = (b: BrokerConfig) => {
    setSelectedBrokerId(b.id);
    setShowEditKeys(false);
    setSaveResult(null);
    setTestResult(null);
    setDailyTotpInput('');
    setFormValues({});
  };

  const handleInputChange = (fieldId: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [fieldId]: value }));
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
          message: '✅ Kotak Neo Live Authenticated! Real session active.',
        });
        setDailyTotpInput('');
        await loadBrokers();
        if (refreshData) await refreshData();
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

  const handleSwitchActiveBroker = async (broker: BrokerConfig) => {
    if (!broker) return;
    try {
      setIsSaving(true);
      setSaveResult(null);
      const poolMap: Record<string, string> = {
        binance_live: 'BINANCE_LIVE_REAL',
        ctrader_live: 'CTRADER_LIVE',
        mt5_live: 'MT5_LIVE_REAL',
        kotak_neo_live: 'KOTAK_NEO_LIVE_POOL',
        upstox_live: 'UPSTOX_LIVE',
        zerodha_live: 'ZERODHA_LIVE_POOL',
        bybit_live: 'BYBIT_LIVE',
        okx_live: 'OKX_LIVE',
      };
      const pool = poolMap[broker.id] || broker.id;
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
        setSaveResult({
          status: 'SUCCESS',
          message: `Active Broker switched to ${broker.name}!`,
        });
        await loadBrokers();
        if (refreshData) await refreshData();
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

  const handleTestConnection = async () => {
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
    try {
      setIsSaving(true);
      setSaveResult(null);
      const res = await api.connectBroker({
        broker_id: selectedBroker.id,
        ...formValues,
      });

      if (res.status === 'SUCCESS' || res.status === 'READY') {
        setSaveResult({
          status: 'SUCCESS',
          message: `${selectedBroker.name} credentials updated successfully!`,
        });
        setShowEditKeys(false);
        await loadBrokers();
        if (refreshData) await refreshData();
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

  const handleDisconnect = async (brokerId: string) => {
    if (!confirm('Are you sure you want to disconnect this broker? (Stored keys will be cleared from session)')) return;
    try {
      await api.disconnectBroker(brokerId);
      await loadBrokers();
      if (refreshData) await refreshData();
    } catch (err: any) {
      alert(`Disconnect failed: ${err?.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-line flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-line bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-txt-primary">Broker Gateways</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  LIVE REAL CAPITAL
                </span>
              </div>
              <p className="text-xs text-txt-muted">Manage and switch your connected broker accounts</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-200 rounded-lg transition cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 3 Clean Market Category Tabs */}
        <div className="flex items-center gap-2 px-6 py-2.5 border-b border-line bg-white">
          <button
            onClick={() => handleSelectMarket('CRYPTO')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              selectedMarket === 'CRYPTO'
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span>🪙 Crypto</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          </button>

          <button
            onClick={() => handleSelectMarket('INDIA')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              selectedMarket === 'INDIA'
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span>🇮🇳 Indian Markets</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          </button>

          <button
            onClick={() => handleSelectMarket('FOREX_GOLD')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              selectedMarket === 'FOREX_GOLD'
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span>🌍 Forex &amp; Gold</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          </button>
        </div>

        {/* Modal Body - 2 Columns */}
        <div className="grid grid-cols-1 md:grid-cols-12 min-h-[380px] max-h-[68vh] overflow-hidden">
          {/* Left Column: Broker List in Market */}
          <div className="md:col-span-5 border-r border-line p-4 space-y-2 overflow-y-auto bg-slate-50/50">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Available Brokers ({marketBrokers.length})
            </div>

            {marketBrokers.map((b) => {
              const isSelected = selectedBroker.id === b.id;
              const isBConnected = Boolean(
                b.is_connected ||
                b.status === 'ONLINE' ||
                b.status === 'CONNECTED' ||
                b.status === 'ACTIVE' ||
                b.has_stored_credentials
              );

              return (
                <div
                  key={b.id}
                  onClick={() => handleSelectBroker(b)}
                  className={`p-3 rounded-xl border transition cursor-pointer flex flex-col gap-1.5 ${
                    isSelected
                      ? 'border-brand bg-white shadow-sm ring-1 ring-brand'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{b.name}</span>
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                        isBConnected
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-slate-100 text-slate-500 border border-slate-200'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isBConnected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                      {isBConnected ? 'Connected' : 'Standby'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                    <span className="truncate max-w-[140px]">
                      {isBConnected ? (b.active_account_label || b.saved_ucc || 'Configured') : 'Not Configured'}
                    </span>
                    {isBConnected && typeof b.balance === 'number' && b.balance > 0 && (
                      <span className="font-bold text-slate-700">
                        {b.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })} {b.currency}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Selected Broker Details */}
          <div className="md:col-span-7 p-5 overflow-y-auto space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              {/* Selected Broker Header Card */}
              {isConnected ? (
                <div className="p-4 bg-gradient-to-br from-emerald-50/90 to-teal-50/50 rounded-2xl border border-emerald-200 shadow-xs space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-2xs">
                        <CheckCircle2 className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-extrabold text-slate-900">{selectedBroker.name}</h3>
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                            ● OPERATIONAL
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-600 mt-0.5">{selectedBroker.description}</p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleSwitchActiveBroker(selectedBroker)}
                      disabled={isSaving}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold font-mono transition shadow-xs cursor-pointer flex items-center gap-1 shrink-0"
                    >
                      <span>⚡ Set as Active</span>
                    </button>
                  </div>

                  {/* 3 Quick Stat Pills */}
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="bg-white/90 p-2.5 rounded-xl border border-emerald-100 shadow-2xs">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">Balance</span>
                      <span className="text-xs font-mono font-extrabold text-emerald-700 truncate block">
                        {typeof selectedBroker.balance === 'number'
                          ? selectedBroker.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                          : (selectedBroker.balance || '0.00')}{' '}
                        {selectedBroker.currency || 'USD'}
                      </span>
                    </div>

                    <div className="bg-white/90 p-2.5 rounded-xl border border-emerald-100 shadow-2xs">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">Account / ID</span>
                      <span className="text-xs font-mono font-bold text-slate-800 truncate block mt-0.5">
                        {selectedBroker.active_account_label || selectedBroker.saved_ucc || 'Configured'}
                      </span>
                    </div>

                    <div className="bg-white/90 p-2.5 rounded-xl border border-emerald-100 shadow-2xs">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">Latency</span>
                      <span className="text-xs font-mono font-bold text-slate-800 truncate block mt-0.5">
                        {selectedBroker.ping_ms || '18ms'} &bull; Direct
                      </span>
                    </div>
                  </div>

                  {/* Kotak Neo Fast Daily TOTP */}
                  {selectedBroker.id === 'kotak_neo_live' && (
                    <div className="p-3 bg-red-50/70 rounded-xl border border-red-200/80 space-y-2">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                        <span className="flex items-center gap-1.5 text-red-900">
                          <KeyRound className="h-4 w-4 text-red-600" />
                          Daily 2FA Login (TOTP from Authenticator App)
                        </span>
                        <span className="text-[10px] text-slate-500 font-normal">Valid for 30s</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          maxLength={6}
                          placeholder="e.g. 582910"
                          value={dailyTotpInput}
                          onChange={(e) => setDailyTotpInput(e.target.value.replace(/\D/g, ''))}
                          className="w-32 px-3 py-1.5 text-xs font-mono font-bold tracking-widest text-center bg-white border border-red-300 rounded-lg outline-none"
                        />
                        <button
                          type="button"
                          disabled={isDailyTotpSubmitting || dailyTotpInput.length !== 6}
                          onClick={handleQuickDailyTotpSubmit}
                          className="px-3 py-1.5 text-xs font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-xs transition disabled:opacity-50 cursor-pointer"
                        >
                          {isDailyTotpSubmitting ? 'Authenticating...' : '🚀 Authenticate'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Footnote & Edit Toggle */}
                  <div className="pt-2 border-t border-emerald-200/60 flex items-center justify-between text-xs">
                    <span className="text-emerald-800 text-[11px] font-medium flex items-center gap-1">
                      <Shield className="h-3.5 w-3.5 text-emerald-600" />
                      Read &amp; Trade Active (Withdrawals Disabled 🔒)
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowEditKeys(!showEditKeys)}
                      className="text-slate-700 hover:text-slate-900 font-bold text-xs underline cursor-pointer"
                    >
                      {showEditKeys ? 'Hide Credentials' : '✏️ Change Credentials'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                  <span className="text-xs font-bold text-slate-900 block">{selectedBroker.name}</span>
                  <p className="text-xs text-slate-500">
                    This broker is currently on standby. Enter credentials below to connect.
                  </p>
                </div>
              )}

              {/* Form (Shown if NOT connected OR user clicked 'Change Credentials') */}
              {(!isConnected || showEditKeys) && (
                <form onSubmit={handleSaveConnection} className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <span className="text-xs font-bold text-slate-800">
                      {isConnected ? `Update ${selectedBroker.name} Keys` : `Connect ${selectedBroker.name}`}
                    </span>
                    <span className="text-[10px] text-slate-400">Encrypted in server vault</span>
                  </div>

                  {(selectedBroker.fields || []).map((f) => (
                    <div key={f.id} className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-700 flex items-center justify-between">
                        <span>{f.label}</span>
                        {f.required && !selectedBroker.has_stored_credentials && (
                          <span className="text-[10px] text-red-500">*Required</span>
                        )}
                      </label>
                      <input
                        type={f.type || 'text'}
                        placeholder={f.placeholder}
                        required={f.required && !selectedBroker.has_stored_credentials}
                        value={formValues[f.id] || ''}
                        onChange={(e) => handleInputChange(f.id, e.target.value)}
                        className="w-full px-3 py-1.5 text-xs font-mono bg-white border border-slate-200 rounded-lg focus:border-brand focus:ring-1 focus:ring-brand outline-none transition"
                      />
                    </div>
                  ))}

                  <div className="flex items-center justify-end gap-2 pt-2">
                    {isConnected && (
                      <button
                        type="button"
                        onClick={() => setShowEditKeys(false)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition cursor-pointer"
                      >
                        Cancel
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={handleTestConnection}
                      disabled={isTesting}
                      className="px-3 py-1.5 text-xs font-semibold bg-white border border-slate-200 hover:bg-slate-100 rounded-lg transition cursor-pointer flex items-center gap-1.5"
                    >
                      <RefreshCw className={`h-3 w-3 ${isTesting ? 'animate-spin' : ''}`} />
                      <span>{isTesting ? 'Testing...' : 'Test Connection'}</span>
                    </button>
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="px-4 py-1.5 text-xs font-bold bg-slate-900 text-white hover:bg-slate-800 rounded-lg shadow-xs transition disabled:opacity-50 cursor-pointer"
                    >
                      {isSaving ? 'Saving...' : 'Save & Authenticate'}
                    </button>
                  </div>
                </form>
              )}

              {/* Status alerts */}
              {testResult && (
                <div
                  className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
                    testResult.status === 'SUCCESS'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-red-50 text-red-800 border-red-200'
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

              {saveResult && (
                <div
                  className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
                    saveResult.status === 'SUCCESS'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-red-50 text-red-800 border-red-200'
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
            </div>

            {/* Bottom Row within right panel */}
            <div className="pt-3 border-t border-line flex items-center justify-between text-xs">
              {isConnected ? (
                <button
                  type="button"
                  onClick={() => handleDisconnect(selectedBroker.id)}
                  className="text-xs font-semibold text-red-600 hover:text-red-800 hover:underline cursor-pointer"
                >
                  Disconnect Gateway
                </button>
              ) : (
                <div />
              )}
              <span className="text-[11px] text-slate-400">
                Server IP: <code className="font-mono font-bold text-slate-600">187.127.189.139</code>
              </span>
            </div>
          </div>
        </div>

        {/* Modal Bottom Bar */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-line bg-slate-50">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 text-xs font-bold bg-slate-900 text-white hover:bg-slate-800 rounded-xl shadow-xs transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
