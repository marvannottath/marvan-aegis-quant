import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface KpiCardProps {
  label: string;
  value: string | number | null | undefined;
  currency?: string;
  change?: number;
  changePeriod?: string;
  context?: string;
  trend?: 'up' | 'down' | 'neutral';
  tooltip?: string;
  highlight?: boolean;
}

export function KpiCard({
  label,
  value,
  currency,
  change,
  changePeriod = '24h',
  context,
  trend,
  tooltip,
  highlight = false,
}: KpiCardProps) {
  // Format numeric values
  const isDisconnected = value === 'DISCONNECTED' || value === 'UNAVAILABLE';
  const displayValue =
    typeof value === 'number'
      ? value.toLocaleString('en-US', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : value ?? '—';

  const derivedTrend =
    trend ||
    (change !== undefined
      ? change > 0
        ? 'up'
        : change < 0
        ? 'down'
        : 'neutral'
      : undefined);

  return (
    <div
      title={tooltip}
      className={`card-panel card-panel-hover p-4 flex flex-col justify-between ${
        highlight ? 'ring-1 ring-brand/30 bg-blue-50/20' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] font-medium uppercase tracking-wider text-txt-muted">
          {label}
        </span>
        {context && (
          <span className="text-[11px] font-mono font-medium text-txt-subtle px-1.5 py-0.5 bg-slate-100 rounded">
            {context}
          </span>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-1.5">
        {currency && (
          <span className="text-sm font-semibold text-txt-muted">{currency}</span>
        )}
        <span className="text-2xl font-bold tracking-tight text-txt-primary tabular-nums">
          {displayValue}
        </span>
      </div>

      {change !== undefined && (
        <div className="mt-2.5 flex items-center gap-1.5 text-xs font-medium">
          {derivedTrend === 'up' && (
            <span className="flex items-center text-profit font-semibold">
              <ArrowUpRight className="h-3.5 w-3.5" />
              +{Math.abs(change).toFixed(2)}%
            </span>
          )}
          {derivedTrend === 'down' && (
            <span className="flex items-center text-loss font-semibold">
              <ArrowDownRight className="h-3.5 w-3.5" />
              -{Math.abs(change).toFixed(2)}%
            </span>
          )}
          {derivedTrend === 'neutral' && (
            <span className="flex items-center text-txt-muted">
              <Minus className="h-3.5 w-3.5" />
              0.00%
            </span>
          )}
          <span className="text-[11px] text-txt-subtle">vs {changePeriod}</span>
        </div>
      )}
    </div>
  );
}
