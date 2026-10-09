'use client';

import React from 'react';
import { KpiHeaderRow } from './KpiHeaderRow';
import { CandlestickChart } from '../chart/CandlestickChart';
import { PerformanceCurveChart } from '../chart/PerformanceCurveChart';
import { QuickOrderConsole } from './QuickOrderConsole';
import { PositionsTable } from '../positions/PositionsTable';
import { MarketWatchList } from './MarketWatchList';
import { OrdersTable } from '../orders/OrdersTable';

export function OverviewDashboard() {
  return (
    <div className="space-y-6">
      {/* 1. Top KPI Row */}
      <KpiHeaderRow />

      {/* 2. Primary Trading Grid: Candlestick Chart + Order Ticket */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <CandlestickChart />
        </div>
        <div className="lg:col-span-1">
          <QuickOrderConsole />
        </div>
      </div>

      {/* 3. Active Positions Data Grid */}
      <PositionsTable />

      {/* 4. Equity Performance Curve + Market Watchlist */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PerformanceCurveChart />
        </div>
        <div className="lg:col-span-1">
          <MarketWatchList />
        </div>
      </div>

      {/* 5. Recent Orders Feed */}
      <OrdersTable />
    </div>
  );
}
