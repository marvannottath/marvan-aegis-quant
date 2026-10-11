'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { KpiCard } from '../common/KpiCard';

export function KpiHeaderRow() {
  const { portfolio, capital, workspace, environment } = useTradingContext();

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

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

  const tradeableCapital = isLiveDisconnected
    ? 'DISCONNECTED'
    : isLoading
    ? '—'
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

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-7 gap-3 sm:gap-4">
      {/* 1. Total Equity */}
      <KpiCard
        label="Total Equity"
        value={totalEquity}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? 'Offline' : environment === 'DEMO' ? 'Paper' : 'Live'}
        tooltip={isLiveDisconnected ? 'Live broker unauthenticated. Real live credentials required; simulation paper fallback strictly blocked.' : 'Authoritative net equity'}
        highlight={true}
      />

      {/* 2. Available Cash */}
      <KpiCard
        label="Available Cash"
        value={availableCash}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? undefined : environment === 'DEMO' ? 'Cash' : 'Settled'}
        tooltip={isLiveDisconnected ? 'Live cash unavailable while broker is disconnected' : 'Free unencumbered liquid cash balance'}
      />

      {/* 3. Tradeable Capital */}
      <KpiCard
        label="Tradeable Capital"
        value={tradeableCapital}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? undefined : 'Net'}
        tooltip={isLiveDisconnected ? 'Trading locked while broker is disconnected' : 'Deployable tradeable capital strictly subtracting margins, reserves, and safety buffer'}
      />

      {/* 4. Unrealized / Today PnL */}
      <KpiCard
        label="Floating PnL"
        value={unrealizedPnL}
        currency={isLiveDisconnected ? undefined : curr}
        context={undefined}
        trend={!isLiveDisconnected && numPnL > 0 ? 'up' : !isLiveDisconnected && numPnL < 0 ? 'down' : 'neutral'}
        change={!isLiveDisconnected && numEquity > 0 ? (numPnL / numEquity) * 100 : undefined}
        changePeriod="equity"
        tooltip={isLiveDisconnected ? 'Floating PnL unavailable while broker is disconnected' : 'Real-time floating unrealized mark-to-market PnL'}
      />

      {/* 5. Open Positions */}
      <KpiCard
        label="Open Positions"
        value={openPositions}
        context={isLiveDisconnected ? undefined : workspace}
        tooltip={isLiveDisconnected ? 'Positions unavailable while broker is disconnected' : 'Count of active broker open positions'}
      />

      {/* 6. Total Exposure */}
      <KpiCard
        label="Exposure"
        value={exposure}
        currency={isLiveDisconnected ? undefined : curr}
        context={undefined}
        change={!isLiveDisconnected && numEquity > 0 ? (numExposure / numEquity) * 100 : undefined}
        changePeriod="leverage"
        tooltip={isLiveDisconnected ? 'Exposure unavailable while broker is disconnected' : 'Gross notional capital exposed in open positions'}
      />

      {/* 7. Drawdown */}
      <KpiCard
        label="Max Drawdown"
        value={drawdown}
        context={isLiveDisconnected ? undefined : 'Peak'}
        tooltip={isLiveDisconnected ? 'Drawdown unavailable while broker is disconnected' : 'Peak-to-trough equity drawdown percentage'}
      />
    </div>
  );
}
