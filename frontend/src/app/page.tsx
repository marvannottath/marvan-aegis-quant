'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { MobileNav } from '@/components/MobileNav';
import { MetricsGrid } from '@/components/MetricsGrid';
import { CircuitBreakerBanner } from '@/components/CircuitBreakerBanner';
import { CapitalConfigurator } from '@/components/CapitalConfigurator';
import { CandlestickChart } from '@/components/CandlestickChart';
import { OrderConsole } from '@/components/OrderConsole';
import { ActivePositionsTable } from '@/components/ActivePositionsTable';
import { LiveOrdersFeed } from '@/components/LiveOrdersFeed';
import { TradeForensicsFeed } from '@/components/TradeForensicsFeed';
import { EquityChart } from '@/components/EquityChart';

const API_BASE = 'http://localhost:8005';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedAsset, setSelectedAsset] = useState('XAUUSD');
  const [systemState, setSystemState] = useState<any>(null);
  const [equityCurve, setEquityCurve] = useState<number[]>([]);

  const fetchState = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/state`);
      if (res.ok) {
        const data = await res.json();
        setSystemState(data);
      }
    } catch (err) {
      console.error("Failed to connect to Aegis-Quant FastAPI Backend:", err);
    }
  };

  const triggerSync = async () => {
    try {
      await fetch(`${API_BASE}/api/run-sync`);
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const resetCircuitBreaker = async () => {
    try {
      await fetch(`${API_BASE}/api/reset-circuit-breaker`, { method: 'POST' });
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const setCapital = async (amount: number) => {
    try {
      await fetch(`${API_BASE}/api/set-capital`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount }),
      });
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleAI = async (active: boolean) => {
    try {
      await fetch(`${API_BASE}/api/toggle-ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active }),
      });
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const placeManualOrder = async (orderData: {
    asset: string;
    action: 'BUY' | 'SELL';
    amount: number;
    leverage: number;
    stopLoss: number;
    takeProfit: number;
  }) => {
    try {
      await fetch(`${API_BASE}/api/place-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset: orderData.asset,
          action: orderData.action,
          amount: orderData.amount,
          leverage: orderData.leverage,
          stop_loss_pct: orderData.stopLoss,
          take_profit_pct: orderData.takeProfit,
        }),
      });
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const closePosition = async (asset: string) => {
    try {
      await fetch(`${API_BASE}/api/close-position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset }),
      });
      fetchState();
    } catch (err) {
      console.error(err);
    }
  };

  const runBacktest = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/run-backtest?ticker=${selectedAsset}`);
      if (res.ok) {
        const data = await res.json();
        if (data.equity_curve) {
          setEquityCurve(data.equity_curve);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchState();
    runBacktest();
    const interval = setInterval(fetchState, 3000);
    return () => clearInterval(interval);
  }, []);

  const defaultAccount = {
    portfolio_equity: 100000.0,
    virtual_cash: 100000.0,
    initial_capital: 100000.0,
    total_pnl_usd: 0.0,
    total_pnl_pct: 0.0,
    open_positions: [],
    ai_active: true,
  };

  const account = systemState?.account || defaultAccount;
  const sentiment = systemState?.daily_sync || { alignment_score: 0.0 };
  const forensics = systemState?.trade_forensics || [];
  const circuitBreaker = systemState?.circuit_breaker || { tripped: false, reason: '' };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar onSync={triggerSync} status={systemState ? `ONLINE (${account.ai_active ? 'AI ACTIVE' : 'AI PAUSED'})` : 'CONNECTING...'} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 md:px-6 py-6 space-y-6">
        <CircuitBreakerBanner
          tripped={circuitBreaker.tripped}
          reason={circuitBreaker.reason}
          onReset={resetCircuitBreaker}
        />

        {/* Top Overview Metrics */}
        <MetricsGrid account={account} sentiment={sentiment} />

        {/* Exchange Pro Layout: Candlestick Chart (Left) + Side Order Execution Console (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <CandlestickChart selectedAsset={selectedAsset} onAssetChange={setSelectedAsset} />
            <ActivePositionsTable positions={account.open_positions || []} onClosePosition={closePosition} />
          </div>

          <div className="space-y-6">
            <OrderConsole
              selectedAsset={selectedAsset}
              virtualCash={account.virtual_cash}
              onPlaceOrder={placeManualOrder}
            />
            <CapitalConfigurator
              initialCapital={account.initial_capital}
              aiActive={account.ai_active ?? true}
              onSetCapital={setCapital}
              onToggleAI={toggleAI}
            />
          </div>
        </div>

        {/* Real-time Order Stream & AI Trade Forensics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LiveOrdersFeed orders={systemState?.live_order_stream || []} />
          <TradeForensicsFeed forensics={forensics} />
        </div>

        {/* Strategy Backtest Curve */}
        <EquityChart equityData={equityCurve} onRunBacktest={runBacktest} />
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <MobileNav activeTab={activeTab} setActiveTab={setActiveTab} />
    </div>
  );
}
