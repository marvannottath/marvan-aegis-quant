'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  CandlestickData,
  ColorType,
} from 'lightweight-charts';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { RefreshCw } from 'lucide-react';

interface CandlestickChartProps {
  initialSymbol?: string;
  onSymbolChange?: (symbol: string) => void;
}

export function CandlestickChart({
  initialSymbol,
  onSymbolChange,
}: CandlestickChartProps) {
  const { environment, workspace } = useTradingContext();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  // Available symbols by workspace
  const defaultSymbols = {
    CRYPTO: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'],
    INDIA: ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'NIFTY50'],
    FOREX_GOLD: ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY'],
  }[workspace] || ['BTCUSDT'];

  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    initialSymbol || defaultSymbols[0]
  );
  const [timeframe, setTimeframe] = useState<string>('1h');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);

  // When workspace changes, reset selected symbol to default
  useEffect(() => {
    const symbols = {
      CRYPTO: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'],
      INDIA: ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY'],
      FOREX_GOLD: ['XAUUSD', 'EURUSD', 'GBPUSD'],
    }[workspace] || ['BTCUSDT'];

    if (!symbols.includes(selectedSymbol)) {
      setSelectedSymbol(symbols[0]);
    }
  }, [workspace, selectedSymbol]);

  // Load and apply chart data
  const loadChartData = useCallback(async () => {
    if (!candleSeriesRef.current) return;
    try {
      setIsLoading(true);
      const data = await api.getChartHistory(selectedSymbol, timeframe, workspace, environment);

      if (data && data.candles && data.candles.length > 0) {
        // Sort chronologically and format
        const sortedCandles = [...data.candles].sort((a, b) => a.time - b.time);

        // Map to lightweight-charts CandlestickData
        const chartData: CandlestickData[] = sortedCandles.map((c) => ({
          time: (c.time > 10000000000 ? Math.floor(c.time / 1000) : c.time) as any,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        candleSeriesRef.current.setData(chartData);

        const latest = sortedCandles[sortedCandles.length - 1];
        const prev = sortedCandles[Math.max(0, sortedCandles.length - 2)];
        setLastPrice(latest.close);
        if (prev && prev.close > 0) {
          setPriceChange(((latest.close - prev.close) / prev.close) * 100);
        }

        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      }
    } catch (err) {
      console.error('Failed to load candlestick data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedSymbol, timeframe, workspace, environment]);

  // Initialize or re-create chart strictly when container mounts or size changes
  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const container = chartContainerRef.current;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 380,
      layout: {
        background: { type: ColorType.Solid, color: '#FFFFFF' },
        textColor: '#475569',
        fontSize: 11,
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
      grid: {
        vertLines: { color: '#F1F5F9' },
        horzLines: { color: '#F1F5F9' },
      },
      crosshair: {
        vertLine: {
          color: '#94A3B8',
          width: 1,
          style: 1,
          labelBackgroundColor: '#0F172A',
        },
        horzLine: {
          color: '#94A3B8',
          width: 1,
          style: 1,
          labelBackgroundColor: '#0F172A',
        },
      },
      rightPriceScale: {
        borderColor: '#E2E8F0',
        textColor: '#64748B',
      },
      timeScale: {
        borderColor: '#E2E8F0',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16A34A',
      downColor: '#DC2626',
      borderVisible: false,
      wickUpColor: '#16A34A',
      wickDownColor: '#DC2626',
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const handleResize = () => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    loadChartData();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [environment, workspace, loadChartData]);

  useEffect(() => {
    loadChartData();
  }, [selectedSymbol, timeframe, loadChartData]);

  const handleSelectSymbol = (sym: string) => {
    setSelectedSymbol(sym);
    if (onSymbolChange) onSymbolChange(sym);
  };

  const timeframes = ['5m', '15m', '1h', '4h', '1d'];

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      {/* Chart Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-b border-line bg-slate-50/50">
        <div className="flex items-center gap-2">
          {/* Symbol Select Buttons */}
          <div className="flex items-center gap-1 bg-white p-0.5 rounded-md border border-line">
            {defaultSymbols.map((sym) => (
              <button
                key={sym}
                onClick={() => handleSelectSymbol(sym)}
                className={`px-2.5 py-1 text-xs font-semibold rounded transition ${
                  selectedSymbol === sym
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-txt-secondary hover:bg-slate-100'
                }`}
              >
                {sym}
              </button>
            ))}
          </div>

          {/* Real-time ticker price & change */}
          {lastPrice !== null && (
            <div className="flex items-baseline gap-2 pl-2">
              <span className="text-sm font-bold font-mono text-txt-primary">
                ${lastPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </span>
              <span
                className={`text-xs font-semibold ${
                  priceChange >= 0 ? 'text-profit' : 'text-loss'
                }`}
              >
                {priceChange >= 0 ? '+' : ''}
                {priceChange.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Timeframe & Action Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-white p-0.5 rounded-md border border-line">
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 text-xs font-mono font-medium rounded transition ${
                  timeframe === tf
                    ? 'bg-brand text-white font-semibold'
                    : 'text-txt-muted hover:bg-slate-100 text-txt-secondary'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          <button
            onClick={() => loadChartData()}
            className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-100 rounded transition"
            title="Refresh chart"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="relative w-full h-[380px] bg-white">
        {isLoading && (
          <div className="absolute inset-0 bg-white/70 backdrop-blur-[1px] flex items-center justify-center z-10">
            <span className="text-xs font-medium text-txt-muted flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-brand" />
              Loading {selectedSymbol} {timeframe} market data...
            </span>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
}
