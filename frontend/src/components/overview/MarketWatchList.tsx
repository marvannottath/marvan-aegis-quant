'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { TrendingUp, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react';

export function MarketWatchList() {
  const { workspace } = useTradingContext();
  const [assets, setAssets] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadScanner = async () => {
    try {
      setIsLoading(true);
      const res = await api.getMarketScanner(workspace);
      setAssets(res.assets || []);
    } catch (err) {
      console.error('Failed to load market scanner:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadScanner();
    const interval = setInterval(loadScanner, 6000);
    return () => clearInterval(interval);
  }, [workspace]);

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-slate-50/50">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-brand" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            {workspace} Market Watch
          </h3>
        </div>
        <button
          onClick={loadScanner}
          className="p-1 text-txt-muted hover:text-txt-primary hover:bg-slate-100 rounded transition"
          title="Refresh watchlist"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="overflow-x-auto max-h-[360px] overflow-y-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line bg-slate-50 text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
              <th className="py-2 px-3">Symbol</th>
              <th className="py-2 px-3 text-right">Price</th>
              <th className="py-2 px-3 text-right">24h Change</th>
              <th className="py-2 px-3 text-right">RSI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {assets.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-txt-muted text-xs">
                  Loading {workspace} asset feeds...
                </td>
              </tr>
            ) : (
              assets.map((item) => {
                const isPos = item.change_24h >= 0;
                return (
                  <tr key={item.symbol} className="table-row-hover">
                    <td className="py-2 px-3 font-mono font-semibold text-txt-primary">
                      {item.symbol}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums text-txt-primary">
                      ${Number(item.price).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums">
                      <span className={`inline-flex items-center ${isPos ? 'text-profit' : 'text-loss'}`}>
                        {isPos ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                        {isPos ? '+' : ''}
                        {Number(item.change_24h).toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-txt-secondary">
                      {item.rsi ? Number(item.rsi).toFixed(1) : '50.0'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
