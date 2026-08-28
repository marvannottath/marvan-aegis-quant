'use client';

import React from 'react';
import { DollarSign, Wallet, TrendingUp, Globe } from 'lucide-react';

interface MetricsGridProps {
  account: {
    portfolio_equity: number;
    virtual_cash: number;
    total_pnl_usd: number;
    total_pnl_pct: number;
  };
  sentiment: {
    alignment_score: number;
  };
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({ account, sentiment }) => {
  const isPos = account.total_pnl_usd >= 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
      {/* Equity Card */}
      <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl relative shadow-xl overflow-hidden">
        <div className="flex items-center justify-between text-gray-400 mb-1">
          <span className="text-[11px] md:text-xs font-semibold uppercase tracking-wider">Portfolio Equity</span>
          <DollarSign className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-xl md:text-2xl font-black text-white">
          ${account.portfolio_equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        <div className={`text-xs font-medium mt-1.5 flex items-center ${isPos ? 'text-emerald-400' : 'text-red-400'}`}>
          <TrendingUp className={`w-3.5 h-3.5 mr-1 ${!isPos ? 'rotate-180' : ''}`} />
          {isPos ? '+' : ''}${account.total_pnl_usd.toFixed(2)} ({isPos ? '+' : ''}{account.total_pnl_pct.toFixed(2)}%)
        </div>
      </div>

      {/* Cash Balance Card */}
      <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl relative shadow-xl overflow-hidden">
        <div className="flex items-center justify-between text-gray-400 mb-1">
          <span className="text-[11px] md:text-xs font-semibold uppercase tracking-wider">Virtual Cash</span>
          <Wallet className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-xl md:text-2xl font-black text-white">
          ${account.virtual_cash.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-[11px] text-gray-400 mt-1.5">Paper Capital ($100k)</div>
      </div>

      {/* Sentiment Card */}
      <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl relative shadow-xl overflow-hidden">
        <div className="flex items-center justify-between text-gray-400 mb-1">
          <span className="text-[11px] md:text-xs font-semibold uppercase tracking-wider">Sentiment Index</span>
          <TrendingUp className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-xl md:text-2xl font-black text-blue-400">
          {sentiment.alignment_score >= 0 ? '+' : ''}{sentiment.alignment_score.toFixed(2)}
        </div>
        <div className="text-[11px] text-gray-400 mt-1.5">Daily Strategy Sync</div>
      </div>

      {/* Gold & Forex Assets Card */}
      <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl relative shadow-xl overflow-hidden">
        <div className="flex items-center justify-between text-gray-400 mb-1">
          <span className="text-[11px] md:text-xs font-semibold uppercase tracking-wider">Asset Focus</span>
          <Globe className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-lg md:text-xl font-black text-amber-300">GOLD (XAU/USD)</div>
        <div className="text-[11px] text-gray-400 mt-1.5">Primary Asset Coverage</div>
      </div>
    </div>
  );
};
