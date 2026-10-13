'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  CandlestickData,
  ColorType,
  LineStyle,
  createSeriesMarkers,
} from 'lightweight-charts';
import { useTradingContext } from '../../context/TradingContext';
import { api, getWebSocketUrl } from '../../lib/api';
import { RefreshCw, Radio, Lock, ZoomIn, ZoomOut, Maximize2, Search, Sparkles } from 'lucide-react';

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
  const markersPluginRef = useRef<any>(null);
  const priceLinesRef = useRef<any[]>([]);
  const lastCandleRef = useRef<CandlestickData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fetchRequestIdRef = useRef<number>(0);

  // Expanded available symbols by workspace
  const defaultSymbols = {
    CRYPTO: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'SUIUSDT'],
    INDIA: ['NIFTY50', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'BHARTIARTL'],
    FOREX_GOLD: ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
  }[workspace] || ['BTCUSDT'];

  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    initialSymbol || defaultSymbols[0]
  );
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showSearch, setShowSearch] = useState<boolean>(false);
  const [timeframe, setTimeframe] = useState<string>('1h');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [feedStatus, setFeedStatus] = useState<string>('CONNECTING');
  const [feedSource, setFeedSource] = useState<string>(
    workspace === 'CRYPTO' ? 'BINANCE_PUBLIC_STREAM' : workspace === 'INDIA' ? 'NSE_PUBLIC_FEED' : 'INTERBANK_PUBLIC_FEED'
  );
  const [lastEventTimeIst, setLastEventTimeIst] = useState<string>('—');
  const [eventAgeSeconds, setEventAgeSeconds] = useState<number>(0);
  const [candleCount, setCandleCount] = useState<number>(0);
  const [activeSignal, setActiveSignal] = useState<any>(null);

  // Sync symbol when initialSymbol prop changes from parent
  useEffect(() => {
    if (initialSymbol && initialSymbol !== selectedSymbol) {
      setSelectedSymbol(initialSymbol);
    }
  }, [initialSymbol]);

  // When workspace changes, reset selected symbol to default
  useEffect(() => {
    const symbols = {
      CRYPTO: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT'],
      INDIA: ['NIFTY50', 'RELIANCE', 'TCS', 'HDFCBANK'],
      FOREX_GOLD: ['XAUUSD', 'EURUSD', 'GBPUSD'],
    }[workspace] || ['BTCUSDT'];

    if (!symbols.includes(selectedSymbol)) {
      setSelectedSymbol(symbols[0]);
    }
  }, [workspace, selectedSymbol]);

  // Load historical candlestick data via REST
  const loadChartData = useCallback(async () => {
    const reqId = ++fetchRequestIdRef.current;
    if (!candleSeriesRef.current) return;

    try {
      setIsLoading(true);
      const data = await api.getChartHistory(selectedSymbol, timeframe, workspace, environment);

      // Discard stale async responses if context changed
      if (reqId !== fetchRequestIdRef.current) return;

      const mStatus = data.market_data_status || (workspace === 'CRYPTO' ? 'LIVE' : 'DATA_UNAVAILABLE');
      const mSource = data.market_data_source || (
        workspace === 'CRYPTO'
          ? 'BINANCE_PUBLIC_STREAM'
          : workspace === 'INDIA'
          ? 'NSE_UNAVAILABLE (UPSTOX_NOT_CONFIGURED)'
          : 'MT5_DISCONNECTED'
      );
      setFeedStatus(mStatus);
      setFeedSource(mSource);
      if (data.last_event_time_ist && data.last_event_time_ist !== 'NONE') {
        setLastEventTimeIst(data.last_event_time_ist);
      }
      if (typeof data.event_age_seconds === 'number') {
        setEventAgeSeconds(data.event_age_seconds);
      }

      if (data && data.candles && data.candles.length > 0) {
        setCandleCount(data.candles.length);
        const sortedCandles = [...data.candles].sort((a, b) => a.time - b.time);

        const chartData: CandlestickData[] = sortedCandles.map((c) => ({
          time: (c.time > 10000000000 ? Math.floor(c.time / 1000) : c.time) as any,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        candleSeriesRef.current.setData(chartData);

        const latest = chartData[chartData.length - 1];
        lastCandleRef.current = latest;
        const prev = chartData[Math.max(0, chartData.length - 2)];
        setLastPrice(latest.close);
        if (typeof data.change_24h === 'number') {
          setPriceChange(data.change_24h);
        } else if (prev && prev.close > 0) {
          setPriceChange(((latest.close - prev.close) / prev.close) * 100);
        }

        if (chartRef.current) {
          const ts = chartRef.current.timeScale();
          ts.resetTimeScale();
          ts.scrollToRealTime();
        }

        // Fetch authoritative AI Quantitative Signals for selected symbol
        try {
          const stateRes = await fetch(`/api/state?workspace=${workspace}&environment=${environment}`);
          if (stateRes.ok) {
            const stateData = await stateRes.json();
            const opps = stateData.ai_opportunities || [];
            const symClean = selectedSymbol.replace('USDT', '').toUpperCase();
            const match = opps.find((o: any) => {
              const oSym = (o.symbol || o.ticker || '').replace('USDT', '').toUpperCase();
              return oSym === symClean || o.symbol === selectedSymbol;
            });

            // Clean up previous price lines
            if (priceLinesRef.current.length > 0 && candleSeriesRef.current) {
              priceLinesRef.current.forEach((pl) => {
                try {
                  candleSeriesRef.current?.removePriceLine(pl);
                } catch {
                  // ignored
                }
              });
              priceLinesRef.current = [];
            }

            if (match && match.action !== 'DISABLED') {
              setActiveSignal(match);
              if (candleSeriesRef.current) {
                // Plot Stop Loss line
                if (match.sl && match.sl > 0) {
                  const slLine = candleSeriesRef.current.createPriceLine({
                    price: match.sl,
                    color: '#DC2626',
                    lineWidth: 1,
                    lineStyle: LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'AI SL',
                  });
                  priceLinesRef.current.push(slLine);
                }
                // Plot Take Profit line
                if (match.tp && match.tp > 0) {
                  const tpLine = candleSeriesRef.current.createPriceLine({
                    price: match.tp,
                    color: '#16A34A',
                    lineWidth: 1,
                    lineStyle: LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: 'AI TP',
                  });
                  priceLinesRef.current.push(tpLine);
                }

                // Plot visual marker on latest candle
                if (markersPluginRef.current && latest) {
                  const isBuy = match.action === 'BUY';
                  const isSell = match.action === 'SELL';
                  markersPluginRef.current.setMarkers([
                    {
                      time: latest.time,
                      position: isBuy ? 'belowBar' : 'aboveBar',
                      color: isBuy ? '#16A34A' : isSell ? '#DC2626' : '#2563EB',
                      shape: isBuy ? 'arrowUp' : isSell ? 'arrowDown' : 'circle',
                      text: `AI ${match.action} (${match.score || match.confidence}%)`,
                    },
                  ]);
                }
              }
            } else {
              setActiveSignal(null);
              if (markersPluginRef.current) {
                markersPluginRef.current.setMarkers([]);
              }
            }
          }
        } catch {
          // Non-critical telemetry fetch
        }
      } else {
        setCandleCount(0);
        lastCandleRef.current = null;
        candleSeriesRef.current.setData([]);
        setLastPrice(null);
        setPriceChange(0);
        setActiveSignal(null);
        if (markersPluginRef.current) {
          markersPluginRef.current.setMarkers([]);
        }
      }
    } catch (err) {
      if (reqId === fetchRequestIdRef.current) {
        console.error('Failed to load candlestick data:', err);
        setCandleCount(0);
        lastCandleRef.current = null;
        candleSeriesRef.current?.setData([]);
        setLastPrice(null);
        setActiveSignal(null);
      }
    } finally {
      if (reqId === fetchRequestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [selectedSymbol, timeframe, workspace, environment]);

  // Connect to live WebSocket stream for real-time tick and kline updates
  useEffect(() => {
    if (workspace !== 'CRYPTO') {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setFeedStatus('DATA_UNAVAILABLE');
      setFeedSource(workspace === 'INDIA' ? 'NSE_UNAVAILABLE (UPSTOX_NOT_CONFIGURED)' : 'MT5_DISCONNECTED');
      return;
    }

    const wsUrl = getWebSocketUrl(workspace, environment);
    if (!wsUrl) return;

    let isSubscribed = true;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      if (!isSubscribed) return;
      socket.send(JSON.stringify({ action: 'set_workspace', workspace }));
      socket.send(JSON.stringify({ action: 'set_environment', environment }));
    };

    socket.onmessage = (event) => {
      if (!isSubscribed) return;
      try {
        const msg = JSON.parse(event.data);

        // 1. Live Ticker Event
        if (msg.event_type === 'MARKET_TICK' && msg.symbol === selectedSymbol) {
          const newPrice = Number(msg.price);
          setLastPrice(newPrice);
          if (typeof msg.change_24h === 'number') {
            setPriceChange(msg.change_24h);
          }
          if (msg.source_time) setLastEventTimeIst(msg.source_time);
          setFeedStatus(msg.status || 'LIVE');
          setFeedSource(msg.source || 'BINANCE_PUBLIC_STREAM');
          setEventAgeSeconds(0.0);

          // Update active candle with new tick
          if (candleSeriesRef.current && lastCandleRef.current) {
            const updatedCandle: CandlestickData = {
              ...lastCandleRef.current,
              close: newPrice,
              high: Math.max(lastCandleRef.current.high, newPrice),
              low: Math.min(lastCandleRef.current.low, newPrice),
            };
            candleSeriesRef.current.update(updatedCandle);
            lastCandleRef.current = updatedCandle;
          }
        }

        // 2. Real-Time Kline Candle Update
        else if (
          msg.event_type === 'KLINE_UPDATE' &&
          msg.symbol === selectedSymbol &&
          msg.interval === timeframe &&
          msg.candle
        ) {
          const c = msg.candle;
          const klineCandle: CandlestickData = {
            time: (c.time > 10000000000 ? Math.floor(c.time / 1000) : c.time) as any,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close),
          };

          if (candleSeriesRef.current) {
            candleSeriesRef.current.update(klineCandle);
            lastCandleRef.current = klineCandle;
            setLastPrice(klineCandle.close);
            if (msg.source_time) setLastEventTimeIst(msg.source_time);
            setFeedStatus('LIVE');
            setFeedSource('BINANCE_PUBLIC_STREAM');
            setEventAgeSeconds(0.0);
          }
        }

        // 3. Stream Status Telemetry
        else if (msg.event_type === 'STREAM_STATUS') {
          if (msg.status) setFeedStatus(msg.status);
          if (msg.provider) setFeedSource(msg.provider);
          if (msg.last_event_time_ist && msg.last_event_time_ist !== 'NONE') {
            setLastEventTimeIst(msg.last_event_time_ist);
          }
          if (typeof msg.event_age_seconds === 'number') {
            setEventAgeSeconds(msg.event_age_seconds);
          }
        }
      } catch (err) {
        // Ignored
      }
    };

    socket.onerror = () => {
      if (isSubscribed) setFeedStatus('RECONNECTING');
    };

    socket.onclose = () => {
      if (isSubscribed && workspace === 'CRYPTO') {
        setFeedStatus('RECONNECTING');
      }
    };

    return () => {
      isSubscribed = false;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    };
  }, [workspace, environment, selectedSymbol, timeframe]);

  // Periodic age increment
  useEffect(() => {
    const ageInterval = setInterval(() => {
      setEventAgeSeconds((prev) => {
        const next = prev + 1.0;
        if (workspace === 'CRYPTO' && next > 5.0 && feedStatus === 'LIVE') {
          setFeedStatus('STALE');
        } else if (workspace === 'CRYPTO' && next > 30.0 && feedStatus === 'STALE') {
          setFeedStatus('DISCONNECTED');
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(ageInterval);
  }, [workspace, feedStatus]);

  // Initialize lightweight chart
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
        rightOffset: 6,
        barSpacing: 9,
        minBarSpacing: 1.5,
        fixLeftEdge: true,
        fixRightEdge: false,
        tickMarkFormatter: (time: number, tickMarkType: number) => {
          const d = new Date(time * 1000);
          if (tickMarkType < 3 || timeframe === '1d' || timeframe === '4h') {
            return d.toLocaleDateString([], { day: '2-digit', month: 'short' });
          }
          return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        },
      },
      localization: {
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          return `${d.toLocaleDateString([], { day: '2-digit', month: 'short' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}`;
        },
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        mouseWheel: true,
        pinch: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16A34A',
      downColor: '#DC2626',
      borderVisible: false,
      wickUpColor: '#16A34A',
      wickDownColor: '#DC2626',
    });

    try {
      const markersPlugin = createSeriesMarkers(candleSeries, []);
      markersPluginRef.current = markersPlugin;
    } catch (e) {
      console.warn('Notice: Markers plugin attachment:', e);
    }

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const handleResize = () => {
      try {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
      } catch (e) { /* ignore disposed */ }
    };
    window.addEventListener('resize', handleResize);

    loadChartData();

    return () => {
      window.removeEventListener('resize', handleResize);
      markersPluginRef.current = null;
      priceLinesRef.current = [];
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
    const formatted = sym.trim().toUpperCase();
    if (!formatted) return;
    setSelectedSymbol(formatted);
    if (onSymbolChange) onSymbolChange(formatted);
    setShowSearch(false);
    setSearchQuery('');
  };

  const handleZoomIn = () => {
    if (chartRef.current) {
      const ts = chartRef.current.timeScale();
      const current = ts.options().barSpacing;
      ts.applyOptions({ barSpacing: Math.min(80, current * 1.35) });
    }
  };

  const handleZoomOut = () => {
    if (chartRef.current) {
      const ts = chartRef.current.timeScale();
      const current = ts.options().barSpacing;
      ts.applyOptions({ barSpacing: Math.max(1.5, current * 0.75) });
    }
  };

  const handleResetZoom = () => {
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  };

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
  const curSymbol = workspace === 'INDIA' ? '₹' : '$';

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      {/* Chart Control Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-b border-line bg-slate-50/50">
        <div className="flex flex-wrap items-center gap-2">
          {/* Symbol Select Buttons */}
          <div className="flex items-center gap-1 bg-white p-0.5 rounded-md border border-line overflow-x-auto max-w-[500px]">
            {defaultSymbols.slice(0, 6).map((sym) => (
              <button
                key={sym}
                onClick={() => handleSelectSymbol(sym)}
                className={`px-2.5 py-1 text-xs font-semibold rounded whitespace-nowrap transition ${
                  selectedSymbol === sym
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-txt-secondary hover:bg-slate-100'
                }`}
              >
                {sym.replace('USDT', '')}
              </button>
            ))}

            {/* Search Custom Symbol Button */}
            <button
              onClick={() => setShowSearch(!showSearch)}
              className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 transition ${
                showSearch ? 'bg-brand text-white' : 'text-txt-muted hover:bg-slate-100'
              }`}
              title="Search all coins & instruments"
            >
              <Search className="h-3 w-3" />
              <span>More</span>
            </button>
          </div>

          {/* Quick Search Popover */}
          {showSearch && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSelectSymbol(searchQuery);
              }}
              className="flex items-center gap-1 bg-white p-1 rounded-md border border-brand shadow-sm animate-in fade-in duration-150"
            >
              <input
                type="text"
                placeholder={workspace === 'CRYPTO' ? 'e.g. DOGE, XRP, PEPE' : workspace === 'INDIA' ? 'e.g. RELIANCE, TCS' : 'e.g. EURUSD, GOLD'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                autoFocus
                className="px-2 py-0.5 text-xs font-mono font-bold uppercase w-36 outline-none bg-transparent"
              />
              <button
                type="submit"
                className="px-2 py-0.5 bg-brand text-white rounded text-[11px] font-semibold hover:bg-brand-hover"
              >
                Load
              </button>
            </form>
          )}

          {/* Real-time ticker price & change */}
          {lastPrice !== null ? (
            <div className="flex items-baseline gap-2 pl-2">
              <span className="text-sm font-bold font-mono text-txt-primary">
                {curSymbol}{lastPrice > 50 ? lastPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : lastPrice.toFixed(4)}
              </span>
              <span
                className={`text-xs font-semibold ${
                  priceChange >= 0 ? 'text-profit' : 'text-loss'
                }`}
                title="24h Price Change (Binance 24hr Ticker)"
              >
                {priceChange >= 0 ? '+' : ''}
                {priceChange.toFixed(2)}%
              </span>
            </div>
          ) : (
            <div className="pl-2">
              <span className="text-xs font-mono font-medium text-txt-muted">
                PRICE UNAVAILABLE
              </span>
            </div>
          )}
        </div>

        {/* Timeframe & Zoom & Telemetry Controls */}
        <div className="flex items-center gap-2">
          {/* Zoom In, Zoom Out, Fit Content */}
          <div className="flex items-center bg-white p-0.5 rounded-md border border-line">
            <button
              onClick={handleZoomIn}
              className="p-1 text-txt-secondary hover:text-txt-primary hover:bg-slate-100 rounded transition"
              title="Zoom In (Candle Width)"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-1 text-txt-secondary hover:text-txt-primary hover:bg-slate-100 rounded transition"
              title="Zoom Out (Candle Width)"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1 text-txt-secondary hover:text-txt-primary hover:bg-slate-100 rounded transition"
              title="Fit Full Chart"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Feed Telemetry Badge */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono border ${
              feedStatus === 'LIVE'
                ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
                : feedStatus === 'STALE'
                ? 'border-amber-300 bg-amber-50 text-amber-900'
                : 'border-slate-300 bg-slate-100 text-slate-700'
            }`}
            title={`Source: ${feedSource} | Event Time: ${lastEventTimeIst} | Age: ${eventAgeSeconds.toFixed(1)}s`}
          >
            <Radio
              className={`h-3 w-3 ${
                feedStatus === 'LIVE'
                  ? 'text-emerald-600 animate-pulse'
                  : feedStatus === 'STALE'
                  ? 'text-amber-600'
                  : 'text-slate-500'
              }`}
            />
            <span className="font-bold">
              {feedStatus === 'LIVE' ? 'FEED: LIVE' : `FEED: ${feedStatus}`}
            </span>
            {feedStatus === 'LIVE' && (
              <span className="text-[10px] text-emerald-700 hidden lg:inline">
                ({eventAgeSeconds < 1 ? '<1s' : `${eventAgeSeconds.toFixed(0)}s`})
              </span>
            )}
          </div>

          {/* Active AI Signal Telemetry Badge */}
          {activeSignal && (
            <div
              className={`flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono border ${
                activeSignal.action === 'BUY'
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
                  : activeSignal.action === 'SELL'
                  ? 'border-red-300 bg-red-50 text-red-900'
                  : 'border-blue-200 bg-blue-50 text-blue-900'
              }`}
              title={`Ensemble Score: ${activeSignal.score || activeSignal.confidence}% | SL: ${activeSignal.sl || '—'} | TP: ${activeSignal.tp || '—'}`}
            >
              <Sparkles className="h-3 w-3 text-brand shrink-0" />
              <span className="font-bold">
                AI {activeSignal.action}
              </span>
              <span className="text-[10px] font-semibold opacity-90 hidden sm:inline">
                ({activeSignal.score || activeSignal.confidence}%)
              </span>
            </div>
          )}

          {/* Timeframe selector */}
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
      <div className="relative w-full h-[440px] bg-white">
        {isLoading && (
          <div className="absolute inset-0 bg-white/70 backdrop-blur-[1px] flex items-center justify-center z-10">
            <span className="text-xs font-medium text-txt-muted flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-brand" />
              Loading {selectedSymbol} {timeframe} market data...
            </span>
          </div>
        )}
        {candleCount === 0 && !isLoading && (
          <div className="absolute inset-0 bg-slate-50/95 flex flex-col items-center justify-center z-10 p-6 text-center">
            <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 mb-3">
              <Lock className="h-5 w-5" />
            </div>
            <span className="font-bold text-sm text-txt-primary">
              {workspace === 'INDIA'
                ? 'Indian Equities (NSE/BSE) Feed Unavailable'
                : workspace === 'FOREX_GOLD'
                ? 'Forex & Gold (MT5) Feed Disconnected'
                : 'Market Data Feed Offline'}
            </span>
            <span className="text-xs text-txt-muted max-w-md mt-1.5 leading-relaxed">
              {workspace === 'INDIA'
                ? 'Real-time NSE/BSE market data requires an authenticated Upstox or Kotak Neo broker session. Aegis-Quant strictly enforces zero synthetic data generation.'
                : workspace === 'FOREX_GOLD'
                ? 'Real-time Forex & Gold tick streams require an active MT5 bridge connection. Aegis-Quant strictly enforces zero synthetic data generation.'
                : `Public market stream for ${selectedSymbol} (${timeframe}) is currently reconnecting.`}
            </span>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
}
