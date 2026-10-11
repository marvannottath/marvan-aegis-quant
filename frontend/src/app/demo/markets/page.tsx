'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../../context/TradingContext';
import { MarketWatchList } from '../../../components/overview/MarketWatchList';
import { CandlestickChart } from '../../../components/chart/CandlestickChart';
import { Badge } from '../../../components/common/Badge';

export default function DemoMarketsPage() {
  const { workspace, environment } = useTradingContext();
  const defaultSym = workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT';
  const [selectedSymbol, setSelectedSymbol] = useState<string>(defaultSym);

  useEffect(() => {
    setSelectedSymbol(workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT');
  }, [workspace]);

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

      <div className="space-y-6">
        {/* Full-Width Expansive Candlestick Trading Chart */}
        <div className="w-full">
          <CandlestickChart initialSymbol={selectedSymbol} onSymbolChange={setSelectedSymbol} />
        </div>

        {/* Full-Width Live Market Watch List Below Chart */}
        <div className="w-full">
          <MarketWatchList onSelectSymbol={setSelectedSymbol} selectedSymbol={selectedSymbol} />
        </div>
      </div>
    </div>
  );
}
