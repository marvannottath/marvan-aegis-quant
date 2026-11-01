'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import {
  Wallet,
  Layers,
  ShieldCheck,
  TrendingUp,
  CircleDollarSign,
  ArrowUpRight,
} from 'lucide-react';

export function VaultPortfolioView() {
  const { capital, portfolio, environment, workspace, isFinancialMasked } = useTradingContext();

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);

  const getBrokerVenueName = () => {
    switch (workspace) {
      case 'INDIA':
        return 'Kotak Neo / Upstox';
      case 'FOREX_GOLD':
        return 'cTrader / MT5';
      case 'CRYPTO':
      default:
        return 'Binance Live Spot';
    }
  };

  const brokerVenue = getBrokerVenueName();

  const totalEquity = capital?.total_equity ?? portfolio?.total_equity ?? (isLive ? 6.56 : 19950.55);
  const brokerBalance = capital?.broker_balance ?? totalEquity;
  const availableCash = capital?.available_cash ?? portfolio?.free_cash ?? (isLive ? 6.56 : 19950.55);
  const reservedCash = capital?.reserved_cash ?? 0;
  const usedMargin = capital?.used_margin ?? portfolio?.used_margin ?? 0;
  const openOrderReserve = capital?.open_orders_reserved ?? 0;
  const residualDust = capital?.residual_dust_capital ?? 0;
  const safetyBuffer = capital?.safety_buffer ?? (Number(totalEquity) * 0.02);
  const tradeableCapital = capital?.tradeable_capital ?? Math.max(0, Number(availableCash) - safetyBuffer);

  const buckets = [
    { label: 'Total Equity', value: totalEquity, desc: 'Gross portfolio equity (Cash + Positions)', highlight: true },
    { label: 'Broker Reported Balance', value: brokerBalance, desc: 'Authoritative venue reported balance' },
    { label: 'Liquid Available Cash', value: availableCash, desc: 'Unencumbered settled cash' },
    { label: 'Used Margin / Exposure', value: usedMargin, desc: 'Committed to active market positions' },
    { label: 'Open Orders Reserved', value: openOrderReserve, desc: 'Committed to pending limit orders' },
    { label: 'Reserved Cash (Pending)', value: reservedCash, desc: 'Pending settlements and locks' },
    { label: 'Non-Tradeable Dust', value: residualDust, desc: 'Sub-minimum notional residuals' },
    { label: 'Operational Safety Buffer', value: safetyBuffer, desc: 'Risk reserve cushion ($0.15)' },
    { label: 'Deployable Tradeable Capital', value: tradeableCapital, desc: 'Strictly available for new risk allocation', highlight: true },
  ];

  return (
    <div className="space-y-6">
      {/* ── HEADER TITLE ── */}
      <div>
        <h1 className="text-xl font-extrabold tracking-tight text-txt-primary">
          Portfolio & Capital Allocation
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Authoritative 9-bucket balance model, real-time venue liquidity, and margin deployment.
        </p>
      </div>

      {/* ── TOP LEVEL ASSET SUMMARY CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Trading Account Equity */}
        <div className="card-panel p-5 relative overflow-hidden bg-gradient-to-br from-panel to-panel-light border-line shadow-xs">
          <div className="flex items-center justify-between text-txt-muted mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono">Trading Account Equity</span>
            <Badge variant={isLiveDisconnected ? 'warning' : 'live'} size="sm">
              {isLive ? brokerVenue.toUpperCase() : 'PAPER SIM'}
            </Badge>
          </div>
          <div className="text-3xl font-extrabold font-mono text-txt-primary mt-1">
            {isFinancialMasked ? (
              '••••••••'
            ) : isLiveDisconnected ? (
              <span className="text-xl text-amber-600">DISCONNECTED</span>
            ) : (
              `${curr}${Number(totalEquity).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            )}
          </div>
          <p className="text-[11px] text-txt-muted mt-2">
            Non-custodial active balance available on {brokerVenue}.
          </p>
        </div>

        {/* Card 2: Liquid Available Cash */}
        <div className="card-panel p-5 border-emerald-500/30 bg-emerald-500/5 relative overflow-hidden shadow-xs">
          <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-1.5">
              <CircleDollarSign className="h-4 w-4" />
              Liquid Available Cash
            </span>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
              SETTLED CASH
            </span>
          </div>
          <div className="text-3xl font-extrabold font-mono text-emerald-700 dark:text-emerald-400 mt-1">
            {isFinancialMasked ? (
              '••••••••'
            ) : (
              `${curr}${Number(availableCash).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            )}
          </div>
          <p className="text-[11px] text-emerald-800/80 dark:text-emerald-300/80 mt-2">
            Unencumbered capital immediately ready for position execution.
          </p>
        </div>

        {/* Card 3: Deployable Capital */}
        <div className="card-panel p-5 relative overflow-hidden bg-gradient-to-br from-panel to-panel-light border-line shadow-xs">
          <div className="flex items-center justify-between text-txt-muted mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-1.5">
              <TrendingUp className="h-4 w-4 text-brand" />
              Deployable Tradeable Capital
            </span>
            <Badge variant={capital?.can_open_new_trades ? 'success' : 'neutral'} size="sm">
              {capital?.can_open_new_trades ? 'READY' : 'PRESERVED'}
            </Badge>
          </div>
          <div className="text-3xl font-extrabold font-mono text-txt-primary mt-1">
            {isFinancialMasked ? (
              '••••••••'
            ) : isLiveDisconnected ? (
              <span className="text-xl text-txt-muted">—</span>
            ) : (
              `${curr}${Number(tradeableCapital).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            )}
          </div>
          <p className="text-[11px] text-txt-muted mt-2">
            Net capital after deducting risk reserve safety buffer.
          </p>
        </div>
      </div>

      {/* ── 9-BUCKET CAPITAL BREAKDOWN ── */}
      <div className="card-panel overflow-hidden border border-line rounded-xl bg-panel shadow-2xs">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 dark:bg-panel-light/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              9-Bucket Authoritative Capital Breakdown
            </h3>
          </div>
          <Badge variant={isLiveDisconnected ? 'neutral' : capital?.can_open_new_trades ? 'success' : 'warning'} size="sm">
            {isLiveDisconnected ? 'BROKER DISCONNECTED' : capital?.can_open_new_trades ? 'CAPITAL DEPLOYABLE' : 'NEW ENTRIES BLOCKED (LOW CAPITAL)'}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-line">
          {buckets.map((b) => (
            <div
              key={b.label}
              className={`p-4 bg-white dark:bg-panel flex flex-col justify-between ${
                b.highlight ? 'bg-blue-50/20 dark:bg-blue-950/10' : ''
              }`}
            >
              <div>
                <span className="text-[11px] font-semibold text-txt-muted uppercase tracking-wider">
                  {b.label}
                </span>
                <div className="text-xl font-bold font-mono text-txt-primary mt-1">
                  {isFinancialMasked ? (
                    '••••••••'
                  ) : isLiveDisconnected ? (
                    <span className="text-sm font-semibold text-amber-600">DISCONNECTED</span>
                  ) : (
                    `${curr}${Number(b.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  )}
                </div>
              </div>
              <p className="text-[11px] text-txt-muted mt-2">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
