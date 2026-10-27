'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useTradingContext } from '../../context/TradingContext';
import { KpiCard } from '../common/KpiCard';

export function KpiHeaderRow() {
  const router = useRouter();
  const { portfolio, capital, workspace, environment } = useTradingContext();

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const isDemo = environment === 'DEMO';
  const routePrefix = isDemo ? '/demo' : '';

  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (portfolio === null || portfolio.broker_connected === false || portfolio.total_equity === null || portfolio.status === 'DISCONNECTED');
  const isLoading = portfolio === null;

  const totalEquity = isLiveDisconnected
    ? 'DISCONNECTED'
    : isLoading
    ? '—'
    : portfolio.total_equity !== null && portfolio.total_equity !== undefined
    ? portfolio.total_equity
    : 'UNAVAILABLE';

  const availableCash = isLiveDisconnected
    ? 'DISCONNECTED'
    : isLoading
    ? '—'
    : portfolio.free_cash !== null && portfolio.free_cash !== undefined
    ? portfolio.free_cash
    : 'UNAVAILABLE';

  const vaultBalance = isLiveDisconnected
    ? 'UNAVAILABLE'
    : isLoading
    ? '—'
    : isLive
    ? 0.0
    : portfolio.vault_balance !== null && portfolio.vault_balance !== undefined
    ? portfolio.vault_balance
    : 0.0;

  const tradeableCapital = isLiveDisconnected
    ? 'DISCONNECTED'
    : isLoading
    ? '—'
    : isLive
    ? availableCash
    : capital?.tradeable_capital !== null && capital?.tradeable_capital !== undefined
    ? capital.tradeable_capital
    : typeof availableCash === 'number'
    ? availableCash
    : 'UNAVAILABLE';

  const unrealizedPnL = isLiveDisconnected
    ? 'UNAVAILABLE'
    : isLoading
    ? '—'
    : portfolio.unrealized_pnl !== null && portfolio.unrealized_pnl !== undefined
    ? portfolio.unrealized_pnl
    : 'UNAVAILABLE';

  const openPositions = isLiveDisconnected
    ? 'UNAVAILABLE'
    : isLoading
    ? '—'
    : portfolio.open_positions_count !== null && portfolio.open_positions_count !== undefined
    ? portfolio.open_positions_count
    : portfolio.snapshot?.positions
    ? portfolio.snapshot.positions.length
    : 'UNAVAILABLE';

  const exposure = isLiveDisconnected
    ? 'UNAVAILABLE'
    : isLoading
    ? '—'
    : portfolio.total_exposure !== null && portfolio.total_exposure !== undefined
    ? portfolio.total_exposure
    : portfolio.used_margin !== null && portfolio.used_margin !== undefined
    ? portfolio.used_margin
    : 'UNAVAILABLE';

  const drawdown = isLiveDisconnected
    ? 'UNAVAILABLE'
    : isLoading
    ? '—'
    : portfolio.drawdown_pct !== null && portfolio.drawdown_pct !== undefined
    ? `${portfolio.drawdown_pct.toFixed(2)}%`
    : 'UNAVAILABLE';

  const numEquity = typeof totalEquity === 'number' ? totalEquity : 0;
  const numPnL = typeof unrealizedPnL === 'number' ? unrealizedPnL : 0;
  const numExposure = typeof exposure === 'number' ? exposure : 0;

  const scrollToOrNavigate = (elementId: string, fallbackUrl: string) => {
    const el = document.getElementById(elementId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      router.push(fallbackUrl);
    }
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-4 2xl:grid-cols-8 gap-3 sm:gap-4">
      {/* 1. Total Equity */}
      <KpiCard
        label="Total Equity"
        value={totalEquity}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? 'Offline' : environment === 'DEMO' ? 'Paper' : 'Live'}
        tooltip={isLiveDisconnected ? 'Live broker unauthenticated. Real live credentials required.' : 'Authoritative net equity (Cash + Margin + Vault)'}
        highlight={true}
        onClick={() => router.push(`${routePrefix}/portfolio`)}
      />

      {/* 2. Available Cash */}
      <KpiCard
        label="Available Cash"
        value={availableCash}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? undefined : environment === 'DEMO' ? 'Cash' : 'Settled'}
        tooltip={isLiveDisconnected ? 'Live cash unavailable while broker is disconnected' : 'Free unencumbered liquid cash balance'}
        onClick={() => router.push(`${routePrefix}/portfolio`)}
      />

      {/* 3. Tradeable Capital (Active Working Margin) */}
      <KpiCard
        label="Working Capital"
        value={tradeableCapital}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? undefined : 'Active'}
        tooltip={isLiveDisconnected ? 'Trading locked while broker is disconnected' : 'Active working capital allocated to autonomous engine (strictly excludes Vault Reserve)'}
        onClick={() => router.push(`${routePrefix}/portfolio`)}
      />

      {/* 4. Secured Profit Vault (Protected Reserve) */}
      <KpiCard
        label="Secured Profit Vault"
        value={vaultBalance}
        currency={isLiveDisconnected ? undefined : curr}
        context="Locked"
        trend={typeof vaultBalance === 'number' && vaultBalance > 0 ? 'up' : 'neutral'}
        tooltip="Quarantined profit reserve protected from drawdowns. Autonomous AI engine is strictly forbidden from risking these funds."
        onClick={() => scrollToOrNavigate('vault-section', `${routePrefix}/portfolio`)}
      />

      {/* 5. Unrealized / Floating PnL */}
      <KpiCard
        label="Floating PnL"
        value={unrealizedPnL}
        currency={isLiveDisconnected ? undefined : curr}
        context={undefined}
        trend={!isLiveDisconnected && numPnL > 0 ? 'up' : !isLiveDisconnected && numPnL < 0 ? 'down' : 'neutral'}
        change={!isLiveDisconnected && numEquity > 0 ? (numPnL / numEquity) * 100 : undefined}
        changePeriod="equity"
        tooltip={isLiveDisconnected ? 'Floating PnL unavailable while broker is disconnected' : 'Real-time floating mark-to-market PnL across active positions'}
        onClick={() => scrollToOrNavigate('performance-section', `${routePrefix}/analytics`)}
      />

      {/* 6. Open Positions */}
      <KpiCard
        label="Open Positions"
        value={openPositions}
        context={isLiveDisconnected ? undefined : workspace}
        tooltip={isLiveDisconnected ? 'Positions unavailable while broker is disconnected' : 'Count of active broker open positions'}
        onClick={() => scrollToOrNavigate('positions-section', `${routePrefix}/positions`)}
      />

      {/* 7. Total Exposure */}
      <KpiCard
        label="Exposure"
        value={exposure}
        currency={isLiveDisconnected ? undefined : curr}
        context={undefined}
        change={!isLiveDisconnected && numEquity > 0 ? (numExposure / numEquity) * 100 : undefined}
        changePeriod="leverage"
        tooltip={isLiveDisconnected ? 'Exposure unavailable while broker is disconnected' : 'Gross notional capital exposed in open positions'}
        onClick={() => scrollToOrNavigate('orders-section', `${routePrefix}/orders`)}
      />

      {/* 8. Drawdown */}
      <KpiCard
        label="Max Drawdown"
        value={drawdown}
        context={isLiveDisconnected ? undefined : 'Peak'}
        tooltip={isLiveDisconnected ? 'Drawdown unavailable while broker is disconnected' : 'Peak-to-trough equity drawdown percentage'}
        onClick={() => router.push(`${routePrefix}/risk`)}
      />
    </div>
  );
}
