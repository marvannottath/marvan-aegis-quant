'use client';

import React from 'react';
import { useTradingContext } from '../../../context/TradingContext';
import { MarketWatchList } from '../../../components/overview/MarketWatchList';
import { CandlestickChart } from '../../../components/chart/CandlestickChart';
import { Badge } from '../../../components/common/Badge';

export default function DemoMarketsPage() {
  const { workspace, environment } = useTradingContext();

  const workspaceLabels = {
    CRYPTO: {
      title: 'Crypto Markets (DEMO)',
      desc: 'Binance Spot Testnet Simulation • BTC, ETH, SOL, BNB',
      tag: 'Binance Testnet',
    },
    INDIA: {
      title: 'India Equities (DEMO)',
      desc: 'Simulated NSE Cash Market',
      tag: 'NSE Paper',
    },
    FOREX_GOLD: {
      title: 'Global Forex & Gold (DEMO)',
      desc: 'Simulated ECN Feeds',
      tag: 'Paper FX',
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
            <Badge variant="demo">{workspaceLabels.tag}</Badge>
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
