'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  AreaSeries,
  AreaData,
  ColorType,
} from 'lightweight-charts';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { TrendingUp, RefreshCw } from 'lucide-react';

interface PerformanceCurveChartProps {
  title?: string;
  metric?: 'equity' | 'pnl' | 'drawdown';
}

export function PerformanceCurveChart({
  title = 'Authoritative Portfolio Equity Curve',
  metric: initialMetric = 'equity',
}: PerformanceCurveChartProps) {
  const { environment, workspace } = useTradingContext();
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  const [metric, setMetric] = useState<'equity' | 'pnl' | 'drawdown'>(initialMetric);
  const [range, setRange] = useState<'1D' | '1W' | '1M' | '3M' | 'ALL'>('1M');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadCurve = useCallback(async () => {
    if (!areaSeriesRef.current) return;
    try {
      setIsLoading(true);
      const res = await api.getPerformanceCurve(metric, range, environment, workspace);

      if (res && res.points && res.points.length > 0) {
        const areaData: AreaData[] = res.points.map((p, idx) => {
          let t: any = Math.floor(new Date(p.timestamp).getTime() / 1000);
          if (isNaN(t) || t <= 0) {
            t = Math.floor(Date.now() / 1000) - (res.points.length - idx) * 3600;
          }
          return {
            time: t,
            value: Number(p.value),
          };
        });

        const deduped: AreaData[] = [];
        let lastTime = 0;
        for (const item of areaData) {
          const t = Number(item.time);
          if (t > lastTime) {
            deduped.push(item);
            lastTime = t;
          }
        }

        if (deduped.length > 0) {
          areaSeriesRef.current.setData(deduped);
          if (chartRef.current) {
            chartRef.current.timeScale().fitContent();
          }
        }
      }
    } catch (err) {
      console.error('Failed to load performance curve:', err);
    } finally {
      setIsLoading(false);
    }
  }, [metric, range, environment, workspace]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const container = chartContainerRef.current;
    const isProfit = metric !== 'drawdown';

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 280,
      layout: {
        background: { type: ColorType.Solid, color: '#FFFFFF' },
        textColor: '#64748B',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#F1F5F9' },
        horzLines: { color: '#F1F5F9' },
      },
      crosshair: {
        vertLine: { color: '#94A3B8', style: 1 },
        horzLine: { color: '#94A3B8', style: 1 },
      },
      rightPriceScale: {
        borderColor: '#E2E8F0',
      },
      timeScale: {
        borderColor: '#E2E8F0',
      },
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: isProfit ? 'rgba(37, 99, 235, 0.28)' : 'rgba(220, 38, 38, 0.28)',
      bottomColor: isProfit ? 'rgba(37, 99, 235, 0.01)' : 'rgba(220, 38, 38, 0.01)',
      lineColor: isProfit ? '#2563EB' : '#DC2626',
      lineWidth: 2,
    });

    chartRef.current = chart;
    areaSeriesRef.current = areaSeries;

    const handleResize = () => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    loadCurve();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [metric, environment, workspace, loadCurve]);

  useEffect(() => {
    loadCurve();
  }, [range, loadCurve]);

  const ranges: Array<'1D' | '1W' | '1M' | '3M' | 'ALL'> = ['1D', '1W', '1M', '3M', 'ALL'];

  return (
    <div className="card-panel flex flex-col overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4 text-brand" />
            <span className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              {title}
            </span>
          </div>

          <div className="flex items-center gap-1 bg-white p-0.5 rounded border border-line text-xs">
            <button
              onClick={() => setMetric('equity')}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                metric === 'equity' ? 'bg-slate-900 text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              Equity
            </button>
            <button
              onClick={() => setMetric('pnl')}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                metric === 'pnl' ? 'bg-slate-900 text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              PnL
            </button>
            <button
              onClick={() => setMetric('drawdown')}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                metric === 'drawdown' ? 'bg-slate-900 text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              Drawdown
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 bg-white p-0.5 rounded border border-line">
            {ranges.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-2 py-0.5 text-xs font-mono font-medium rounded transition ${
                  range === r
                    ? 'bg-brand text-white font-semibold'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <button
            onClick={() => loadCurve()}
            className="p-1 text-txt-muted hover:text-txt-primary hover:bg-slate-100 rounded transition"
            title="Refresh performance curve"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="relative w-full h-[280px] bg-white">
        {isLoading && (
          <div className="absolute inset-0 bg-white/70 backdrop-blur-[1px] flex items-center justify-center z-10">
            <span className="text-xs font-medium text-txt-muted flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-brand" />
              Loading curve...
            </span>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
}
