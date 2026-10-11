'use client';

import React from 'react';
import { KpiHeaderRow } from './KpiHeaderRow';
import { CandlestickChart } from '../chart/CandlestickChart';
import { PerformanceCurveChart } from '../chart/PerformanceCurveChart';
import { PositionsTable } from '../positions/PositionsTable';
import { MarketWatchList } from './MarketWatchList';
import { OrdersTable } from '../orders/OrdersTable';
import { AIAutoTradeControl } from '../common/AIAutoTradeControl';
import { ProfitVaultOverviewCard } from './ProfitVaultOverviewCard';
import { useTradingContext } from '../../context/TradingContext';

export function OverviewDashboard() {
  const { workspace } = useTradingContext();
  const defaultSym = workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT';
  const [selectedSymbol, setSelectedSymbol] = React.useState<string>(defaultSym);

  React.useEffect(() => {
    setSelectedSymbol(workspace === 'INDIA' ? 'RELIANCE' : workspace === 'FOREX_GOLD' ? 'XAUUSD' : 'BTCUSDT');
  }, [workspace]);

  return (
    <div className="space-y-6">
      {/* 1. Top KPI Row */}
      <KpiHeaderRow />

      {/* 2. AI Autonomous Trading Control Strip */}
      <AIAutoTradeControl variant="banner" />

      {/* 3. Secured Profit Vault & Capital Quarantine Reserve */}
      <ProfitVaultOverviewCard />

      {/* 4. Primary Candlestick Chart (Full-Width, expansive institutional view) */}
      <div className="w-full">
        <CandlestickChart initialSymbol={selectedSymbol} onSymbolChange={setSelectedSymbol} />
      </div>

      {/* 3. Active Positions Data Grid */}
      <PositionsTable />

      {/* 4. Equity Performance Curve & Drawdown Trajectory (Full-Width) */}
      <div className="w-full">
        <PerformanceCurveChart />
      </div>

      {/* 5. Real-Time Multi-Asset Market Watchlist (Full-Width table down below) */}
      <div className="w-full">
        <MarketWatchList selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />
      </div>

      {/* 6. Recent Orders Feed */}
      <OrdersTable />
    </div>
  );
}
