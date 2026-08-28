'use client';

import React from 'react';
import { Activity, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react';

interface LiveOrder {
  timestamp: string;
  asset: string;
  action: string;
  price: number;
  amount_usd: number;
  reasoning: string;
}

interface LiveOrdersFeedProps {
  orders: LiveOrder[];
}

export const LiveOrdersFeed: React.FC<LiveOrdersFeedProps> = ({ orders }) => {
  if (!orders || orders.length === 0) {
    return (
      <div className="bg-darkcard border border-darkborder p-4 rounded-2xl shadow-xl space-y-2">
        <div className="flex items-center space-x-2 text-blue-400 font-bold text-sm">
          <Activity className="w-4 h-4 animate-spin" />
          <span>Autonomous AI Live Market Loop Active...</span>
        </div>
        <p className="text-xs text-gray-500">Scanning real-time price ticks for EUR/USD & GBP/USD. Autonomous BUY/SELL orders will appear here continuously.</p>
      </div>
    );
  }

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-darkborder pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-bold text-white">Live AI Order Stream</h2>
            <p className="text-[11px] md:text-xs text-gray-400">Real-time Autonomous Execution Log (Zero Clicking Required)</p>
          </div>
        </div>
        <span className="text-[10px] text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 animate-pulse">
          LIVE STREAM
        </span>
      </div>

      <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
        {orders.map((item, idx) => {
          const isBuy = item.action === 'BUY';
          const isSell = item.action === 'SELL';
          const badgeClass = isBuy
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            : isSell
            ? 'bg-red-500/10 text-red-400 border-red-500/30'
            : 'bg-blue-500/10 text-blue-400 border-blue-500/30';

          return (
            <div key={idx} className="p-3 bg-gray-900/90 border border-gray-800 rounded-xl flex items-center justify-between shadow-sm hover:border-gray-700 transition">
              <div className="flex items-center space-x-3">
                <span className={`px-2.5 py-0.5 text-xs font-black rounded-md border flex items-center ${badgeClass}`}>
                  {isBuy && <ArrowUpRight className="w-3 h-3 mr-1" />}
                  {isSell && <ArrowDownRight className="w-3 h-3 mr-1" />}
                  {!isBuy && !isSell && <RefreshCw className="w-3 h-3 mr-1" />}
                  {item.action}
                </span>
                <div>
                  <div className="text-xs font-bold text-white">{item.asset} @ ${item.price.toFixed(4)}</div>
                  <div className="text-[10px] text-gray-400">{item.reasoning}</div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs font-bold text-gray-200">${item.amount_usd.toLocaleString()}</div>
                <div className="text-[10px] text-gray-500">{item.timestamp}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
