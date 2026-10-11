'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { MarketWatchList } from '../../components/overview/MarketWatchList';
import { CandlestickChart } from '../../components/chart/CandlestickChart';
import { Badge } from '../../components/common/Badge';

export default function MarketsPage() {
  const { workspace, environment } = useTradingContext();
  const defaultSym = workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT';
  const [selectedSymbol, setSelectedSymbol] = useState<string>(defaultSym);

  useEffect(() => {
    setSelectedSymbol(workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT');
  }, [workspace]);

  const workspaceLabels = {
    CRYPTO: {
      title: 'Crypto Markets',
      desc: 'Binance Spot Execution Venue • BTC, ETH, SOL, BNB, XRP, DOGE',
      tag: 'Binance Spot',
    },
    INDIA: {
      title: 'India Equities & Indices',
      desc: 'NSE / BSE Cash Market & Index Derivatives • RELIANCE, TCS, HDFC, INFY, NIFTY 50',
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
