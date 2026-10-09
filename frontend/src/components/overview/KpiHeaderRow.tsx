'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { KpiCard } from '../common/KpiCard';

export function KpiHeaderRow() {
  const { portfolio, capital, workspace, environment } = useTradingContext();

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

  const isLiveDisconnected = environment === 'LIVE' && (portfolio?.broker_connected === false || portfolio?.total_equity === null);
  const totalEquity = isLiveDisconnected ? 'DISCONNECTED' : (portfolio?.total_equity ?? capital?.total_equity ?? 0);
  const availableCash = isLiveDisconnected ? 'DISCONNECTED' : (portfolio?.free_cash ?? capital?.available_cash ?? 0);
  const tradeableCapital = isLiveDisconnected ? 'DISCONNECTED' : (capital?.tradeable_capital ?? (typeof availableCash === 'number' ? availableCash : 0));
  const todayPnL = portfolio?.realized_pnl ?? 0;
  const unrealizedPnL = portfolio?.unrealized_pnl ?? 0;
  const openPositions = isLiveDisconnected ? 0 : (portfolio?.open_positions_count ?? portfolio?.snapshot?.positions?.length ?? 0);
  const exposure = isLiveDisconnected ? 0 : (portfolio?.total_exposure ?? portfolio?.used_margin ?? 0);
  const drawdown = portfolio?.drawdown_pct ?? 0;

  const numEquity = typeof totalEquity === 'number' ? totalEquity : 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
      {/* 1. Total Equity */}
      <KpiCard
        label="Total Equity"
        value={totalEquity}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? 'UNAUTHENTICATED' : environment === 'DEMO' ? 'SIMULATED PAPER' : 'LIVE BROKER'}
        tooltip={isLiveDisconnected ? 'Live broker unauthenticated. Real live credentials required; simulation paper fallback strictly blocked.' : 'Authoritative net equity'}
        highlight={true}
      />

      {/* 2. Available Cash */}
      <KpiCard
        label="Available Cash"
        value={availableCash}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? 'UNAVAILABLE' : environment === 'DEMO' ? 'SIMULATED' : 'SETTLED'}
        tooltip={isLiveDisconnected ? 'Live cash unavailable while broker is disconnected' : 'Free unencumbered liquid cash balance'}
      />

      {/* 3. Tradeable Capital */}
      <KpiCard
        label="Tradeable Capital"
        value={tradeableCapital}
        currency={isLiveDisconnected ? undefined : curr}
        context={isLiveDisconnected ? 'LOCKED' : 'NET BUFFER'}
        tooltip={isLiveDisconnected ? 'Trading locked while broker is disconnected' : 'Deployable tradeable capital strictly subtracting margins, reserves, and safety buffer'}
      />

      {/* 4. Unrealized / Today PnL */}
      <KpiCard
        label="Floating PnL"
        value={isLiveDisconnected ? 0 : unrealizedPnL}
        currency={curr}
        trend={unrealizedPnL > 0 ? 'up' : unrealizedPnL < 0 ? 'down' : 'neutral'}
        change={numEquity > 0 ? (unrealizedPnL / numEquity) * 100 : 0}
        changePeriod="equity"
        tooltip="Real-time floating unrealized mark-to-market PnL"
      />

      {/* 5. Open Positions */}
      <KpiCard
        label="Open Positions"
        value={openPositions}
        context={workspace}
        tooltip="Count of active broker open positions"
      />

      {/* 6. Total Exposure */}
      <KpiCard
        label="Exposure"
        value={exposure}
        currency={curr}
        change={numEquity > 0 ? (exposure / numEquity) * 100 : 0}
        changePeriod="leverage"
        tooltip="Gross notional capital exposed in open positions"
      />

      {/* 7. Drawdown */}
      <KpiCard
        label="Max Drawdown"
        value={`${drawdown.toFixed(2)}%`}
        trend={drawdown > 5 ? 'down' : 'neutral'}
        context="Peak"
        tooltip="Peak-to-trough equity drawdown percentage"
      />
    </div>
  );
}
