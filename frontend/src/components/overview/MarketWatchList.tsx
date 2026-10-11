'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api, getWebSocketUrl } from '../../lib/api';
import { Badge } from '../common/Badge';
import {
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Search,
  Zap,
  Sparkles,
  Layers,
  ChevronRight,
  Activity,
} from 'lucide-react';

interface MarketWatchListProps {
  onSelectSymbol?: (symbol: string) => void;
  selectedSymbol?: string;
}

export function MarketWatchList({ onSelectSymbol, selectedSymbol }: MarketWatchListProps = {}) {
  const { workspace, environment } = useTradingContext();
  const [assets, setAssets] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeCategory, setActiveCategory] = useState<string>('ALL');
  const [lastTickTime, setLastTickTime] = useState<string>('—');
  const wsRef = useRef<WebSocket | null>(null);

  const loadScanner = async () => {
    try {
      setIsLoading(true);
      const res = await api.getMarketScanner(workspace);
      const list = (res as any)?.assets || (res as any)?.data || [];
      setAssets(list);
    } catch (err) {
      console.error('Failed to load market scanner:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadScanner();
    const interval = setInterval(loadScanner, 5000);
    return () => clearInterval(interval);
  }, [workspace]);

  // Connect to WebSocket stream to update prices in real time for Crypto
  useEffect(() => {
    if (workspace !== 'CRYPTO') {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const wsUrl = getWebSocketUrl(workspace, environment);
    if (!wsUrl) return;

    let isSubscribed = true;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onmessage = (event) => {
      if (!isSubscribed) return;
      try {
        const msg = JSON.parse(event.data);
        if (msg.event_type === 'MARKET_TICK' && msg.symbol) {
          const sym = msg.symbol;
          const newPrice = Number(msg.price);
          const newChange = typeof msg.change_24h === 'number' ? msg.change_24h : 0.0;
          if (msg.source_time) setLastTickTime(msg.source_time);

          setAssets((prev) =>
            prev.map((item) => {
              if (item.symbol === sym) {
                return {
                  ...item,
                  price: newPrice,
                  change_24h: newChange,
                  status: 'LIVE',
                  source: 'BINANCE_PUBLIC_STREAM',
                };
              }
              return item;
            })
          );
        }
      } catch (err) {
        // Ignored
      }
    };

    return () => {
      isSubscribed = false;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    };
  }, [workspace, environment]);

  // Reset search and category filter on workspace change
  useEffect(() => {
    setSearchQuery('');
    setActiveCategory('ALL');
  }, [workspace]);

  // Available categories based on workspace
  const categories = useMemo(() => {
    if (workspace === 'INDIA') {
      return [
        { id: 'ALL', label: 'ALL ASSETS' },
        { id: 'STOCKS', label: 'STOCKS (NSE)' },
        { id: 'INDICES', label: 'INDICES (NIFTY)' },
        { id: 'ETFS', label: 'ETFS' },
      ];
    }
    if (workspace === 'FOREX_GOLD') {
      return [
        { id: 'ALL', label: 'ALL VENUES' },
        { id: 'FOREX', label: 'FX MAJORS' },
        { id: 'METALS', label: 'GOLD & METALS' },
      ];
    }
    return [
      { id: 'ALL', label: 'ALL PAIRS' },
      { id: 'MAJOR', label: 'MAJORS' },
      { id: 'ALTS', label: 'ALTS' },
    ];
  }, [workspace]);

  // Stream badge metadata
  const streamInfo = useMemo(() => {
    switch (workspace) {
      case 'INDIA':
        return {
          title: 'India Equity Watch',
          provider: 'NSE REAL-TIME FEED',
          color: 'emerald',
        };
      case 'FOREX_GOLD':
        return {
          title: 'Forex & Gold Watch',
          provider: 'INTERBANK OTC FEED',
          color: 'blue',
        };
      case 'CRYPTO':
      default:
        return {
          title: 'Crypto Market Watch',
          provider: 'BINANCE LIVE STREAM',
          color: 'emerald',
        };
    }
  }, [workspace]);

  // Filtered assets based on search query and category
  const filteredAssets = useMemo(() => {
    return assets.filter((item) => {
      // Search filter
      const q = searchQuery.trim().toUpperCase();
      if (q && !item.symbol.toUpperCase().includes(q) && !(item.category || '').toUpperCase().includes(q)) {
        return false;
      }

      // Category filter
      if (activeCategory === 'ALL') return true;
      const cat = (item.category || '').toUpperCase();
      const sym = item.symbol.toUpperCase();

      if (workspace === 'INDIA') {
        if (activeCategory === 'STOCKS') return cat.includes('STOCK') || (!sym.includes('NIFTY') && !sym.includes('BEES'));
        if (activeCategory === 'INDICES') return cat.includes('INDEX') || sym === 'NIFTY50' || sym === 'BANKNIFTY';
        if (activeCategory === 'ETFS') return cat.includes('ETF') || sym.includes('BEES');
      }

      if (workspace === 'FOREX_GOLD') {
        if (activeCategory === 'FOREX') return cat.includes('FOREX') || sym.includes('USD') || sym.includes('EUR') || sym.includes('GBP');
        if (activeCategory === 'METALS') return cat.includes('COMMODIT') || sym.includes('XAU') || sym.includes('GOLD');
      }

      if (workspace === 'CRYPTO') {
        if (activeCategory === 'MAJOR') return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'].includes(sym);
        if (activeCategory === 'ALTS') return !['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'].includes(sym);
      }

      return true;
    });
  }, [assets, searchQuery, activeCategory, workspace]);

  const currSymbol = workspace === 'INDIA' ? '₹' : '$';

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-3.5 border-b border-line bg-slate-50/50 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-brand shrink-0" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            {streamInfo.title}
          </h3>
          <span className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{streamInfo.provider}</span>
          </span>
        </div>

        <button
          onClick={loadScanner}
          disabled={isLoading}
          className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-100 rounded-md transition cursor-pointer"
          title="Refresh watchlist"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Search Input & Category Pills */}
      <div className="p-2.5 border-b border-line bg-white space-y-2">
        {/* Search */}
        <div className="relative">
          <Search className="h-3.5 w-3.5 text-txt-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={`Search ${assets.length} ${workspace} instruments...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs font-mono rounded-lg border border-line bg-slate-50/50 text-txt-primary placeholder:text-txt-subtle focus:bg-white focus:outline-none focus:ring-1 focus:ring-brand"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-txt-muted hover:text-txt-primary text-[11px] font-bold"
            >
              ✕
            </button>
          )}
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 no-scrollbar">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md font-mono uppercase tracking-wider transition whitespace-nowrap cursor-pointer ${
                activeCategory === cat.id
                  ? 'bg-brand text-white shadow-xs'
                  : 'bg-slate-100 text-txt-muted hover:text-txt-primary hover:bg-slate-200/70'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Asset List Table */}
      <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-50 z-10 border-b border-line shadow-xs">
            <tr className="text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
              <th className="py-2.5 px-3">Instrument</th>
              <th className="py-2.5 px-3 text-right">LTP ({currSymbol})</th>
              <th className="py-2.5 px-3 text-right">24h Chg</th>
              <th className="py-2.5 px-3 text-center">AI Signal</th>
              <th className="py-2.5 px-3 text-right">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {filteredAssets.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-txt-muted text-xs">
                  {isLoading ? `Loading ${workspace} live feeds...` : `No matching instruments found`}
                </td>
              </tr>
            ) : (
              filteredAssets.map((item) => {
                const hasPrice = item.price !== null && item.price !== undefined && Number(item.price) > 0;
                const changeVal = typeof item.change_24h === 'number' ? item.change_24h : (parseFloat(item.change_24h) || 0);
                const isPos = changeVal >= 0;
                const priceVal = Number(item.price) || 0;
                const scoreVal = Math.round(Number(item.score ?? 50));
                const action = (item.action || item.direction || 'HOLD').toUpperCase();

                const isSelected =
                  selectedSymbol === item.symbol ||
                  selectedSymbol?.replace('USDT', '') === item.symbol.replace('USDT', '');

                return (
                  <tr
                    key={item.symbol}
                    onClick={() => onSelectSymbol && onSelectSymbol(item.symbol)}
                    className={`transition group cursor-pointer ${
                      isSelected
                        ? 'bg-blue-50/90 font-bold border-l-3 border-brand text-brand'
                        : 'hover:bg-slate-50/80 text-txt-primary'
                    }`}
                    title={onSelectSymbol ? `Click to chart and load ${item.symbol} in execution console` : undefined}
                  >
                    {/* Instrument */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <div>
                          <div className="font-mono font-bold leading-tight">
                            {item.symbol}
                          </div>
                          <div className="text-[10px] text-txt-muted font-sans capitalize mt-0.5">
                            {item.category || (workspace === 'INDIA' ? 'NSE Cash' : 'Instrument')}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Price */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      {hasPrice ? (
                        <div className="font-bold">
                          {currSymbol}
                          {priceVal >= 100
                            ? priceVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                            : priceVal >= 1
                            ? priceVal.toFixed(2)
                            : priceVal.toFixed(4)}
                        </div>
                      ) : (
                        <span className="text-txt-muted text-[11px]">UNAVAILABLE</span>
                      )}
                    </td>

                    {/* 24h Change */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      {hasPrice ? (
                        <span
                          className={`inline-flex items-center gap-0.5 font-bold ${
                            isPos ? 'text-profit' : 'text-loss'
                          }`}
                        >
                          {isPos ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                          {isPos ? '+' : ''}
                          {changeVal.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-txt-muted">—</span>
                      )}
                    </td>

                    {/* AI Signal */}
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                          action === 'BUY'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : action === 'SELL'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {action}
                      </span>
                    </td>

                    {/* Opportunity Score */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      <span className="text-[11px] font-semibold text-txt-secondary">
                        {scoreVal}/100
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="px-4 py-2 border-t border-line bg-slate-50/50 flex items-center justify-between text-[11px] text-txt-muted font-mono">
        <span>Click any row to load into Chart & Execution Console</span>
        <span className="font-bold text-txt-primary">
          {filteredAssets.length} of {assets.length} Assets
        </span>
      </div>
    </div>
  );
}
