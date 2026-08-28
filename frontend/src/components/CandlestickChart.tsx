'use client';

import React, { useState, useEffect } from 'react';
import { LineChart, BarChart2, Clock } from 'lucide-react';

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  selectedAsset: string;
  onAssetChange: (asset: string) => void;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({ selectedAsset, onAssetChange }) => {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [interval, setInterval] = useState('1h');
  const [latestPrice, setLatestPrice] = useState<number>(0);
  const [priceChange, setPriceChange] = useState<number>(0);

  const fetchKlines = async () => {
    try {
      const res = await fetch(`http://localhost:8005/api/klines?ticker=${selectedAsset}`);
      if (res.ok) {
        const data = await res.json();
        setCandles(data.candles || []);
        if (data.candles && data.candles.length > 0) {
          const last = data.candles[data.candles.length - 1];
          const prev = data.candles[0];
          setLatestPrice(last.close);
          const chg = ((last.close - prev.open) / prev.open) * 100;
          setPriceChange(chg);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchKlines();
    const timer = setInterval(fetchKlines, 4000);
    return () => clearInterval(timer);
  }, [selectedAsset]);

  const isUp = priceChange >= 0;

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      {/* Top Asset Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-darkborder pb-3.5">
        <div className="flex items-center space-x-3">
          <select
            value={selectedAsset}
            onChange={(e) => onAssetChange(e.target.value)}
            className="bg-gray-900 border border-gray-700 text-white font-black text-base md:text-lg rounded-xl px-3 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="XAUUSD">GOLD Spot / USD (XAU/USD)</option>
            <option value="EURUSD">EUR / USD (Forex)</option>
            <option value="GBPUSD">GBP / USD (Forex)</option>
            <option value="USDJPY">USD / JPY (Forex)</option>
            <option value="BTCUSD">BTC / USD (Crypto)</option>
            <option value="XLK">XLK (Tech ETF)</option>
          </select>

          <div>
            <div className="text-lg md:text-xl font-black text-white">${latestPrice.toFixed(4)}</div>
            <div className={`text-xs font-bold ${isUp ? 'text-emerald-400' : 'text-red-400'}`}>
              {isUp ? '+' : ''}{priceChange.toFixed(2)}% (24h)
            </div>
          </div>
        </div>

        {/* Timeframe selector */}
        <div className="flex items-center space-x-1 bg-gray-900 p-1 rounded-xl border border-gray-800">
          {['1m', '5m', '1h', '1D'].map((tf) => (
            <button
              key={tf}
              onClick={() => setInterval(tf)}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${
                interval === tf ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Candlestick Visualization */}
      <div className="h-64 md:h-80 w-full relative bg-gray-950/60 rounded-xl border border-gray-800/80 p-3 flex flex-col justify-between">
        <div className="flex-1 flex items-end justify-between space-x-1 pt-4 pb-2 px-2 overflow-hidden">
          {candles.map((candle, idx) => {
            const candleUp = candle.close >= candle.open;
            const barColor = candleUp ? 'bg-emerald-500' : 'bg-red-500';
            const wickColor = candleUp ? 'bg-emerald-400' : 'bg-red-400';

            const range = Math.max(0.0001, candle.high - candle.low);
            const bodyHeightPct = Math.max(8, (Math.abs(candle.close - candle.open) / range) * 100);

            return (
              <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group relative">
                {/* Candle Wick */}
                <div className={`w-[1.5px] ${wickColor} opacity-70 h-full max-h-[85%]`} />
                {/* Candle Body */}
                <div
                  className={`w-full rounded-xs transition-all ${barColor} shadow-sm group-hover:brightness-125`}
                  style={{ height: `${bodyHeightPct}%` }}
                />

                {/* Tooltip on hover */}
                <div className="hidden group-hover:block absolute bottom-full mb-2 z-30 bg-gray-900 text-[10px] text-white p-2 rounded border border-gray-700 whitespace-nowrap shadow-xl">
                  <div>O: {candle.open} | H: {candle.high}</div>
                  <div>L: {candle.low} | C: {candle.close}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Time Axis */}
        <div className="flex justify-between text-[10px] text-gray-500 border-t border-gray-800/80 pt-2 px-1">
          <span>{candles[0]?.time || '00:00'}</span>
          <span>{candles[Math.floor(candles.length / 2)]?.time || '12:00'}</span>
          <span>{candles[candles.length - 1]?.time || '23:59'}</span>
        </div>
      </div>
    </div>
  );
};
