'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { MarketWatchList } from '../../components/overview/MarketWatchList';
import { CandlestickChart } from '../../components/chart/CandlestickChart';
import { Badge } from '../../components/common/Badge';

export default function MarketsPage() {
  const { workspace, environment } = useTradingContext();

  const workspaceLabels = {
    CRYPTO: {
      title: 'Crypto Markets',
      desc: 'Binance Spot Execution Venue • BTC, ETH, SOL, BNB',
      tag: 'Binance Spot',
    },
    INDIA: {
      title: 'India Equities & Indices',
      desc: 'NSE / BSE Cash Market & Index Derivatives • RELIANCE, TCS, HDFC, INFY',
      tag: 'NSE Cash',
    },
    FOREX_GOLD: {
      title: 'Global Forex & Commodities',
      desc: 'Spot Gold (XAUUSD) & Major FX Pairs • EURUSD, GBPUSD',
      tag: 'Institutional ECN',
    },
  }[workspace];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-txt-primary">
              {workspaceLabels.title}
            </h1>
            <Badge variant="info">{workspaceLabels.tag}</Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            {workspaceLabels.desc} ({environment} context)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <CandlestickChart />
        </div>
        <div className="lg:col-span-1">
          <MarketWatchList />
        </div>
      </div>
    </div>
  );
}
