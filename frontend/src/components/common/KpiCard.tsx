import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { useTradingContext } from '../../context/TradingContext';

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
  onClick?: () => void;
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
  onClick,
}: KpiCardProps) {
  const { isFinancialMasked } = useTradingContext();

  // Format numeric values
  const isDisconnected = value === 'DISCONNECTED' || value === 'UNAVAILABLE';
  const displayValue =
    isFinancialMasked && typeof value === 'number'
      ? '••••••'
      : typeof value === 'number'
      ? value.toLocaleString('en-US', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : isDisconnected
      ? '—'
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
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      title={tooltip ? `${tooltip}${onClick ? ' (Click to navigate)' : ''}` : onClick ? 'Click to navigate' : undefined}
      className={`card-panel card-panel-hover p-3.5 sm:p-4 flex flex-col justify-between overflow-hidden transition-all duration-150 ${
        onClick ? 'cursor-pointer hover:border-brand/60 hover:shadow-md active:scale-[0.985] group select-none' : ''
      } ${
        highlight ? 'ring-1 ring-brand/30 bg-blue-50/20' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-1.5 min-w-0">
        <span className={`text-[11px] font-bold uppercase tracking-wider truncate min-w-0 ${
          onClick ? 'text-txt-muted group-hover:text-brand transition-colors' : 'text-txt-muted'
        }`}>
          {label}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {context && (
            <span className="text-[10px] font-mono font-semibold text-txt-subtle px-1.5 py-0.5 bg-slate-100 dark:bg-panel-light rounded shrink-0 whitespace-nowrap">
              {context}
            </span>
          )}
          {onClick && (
            <span className="text-[10px] font-mono text-txt-subtle opacity-0 group-hover:opacity-100 transition-opacity">
              ↗
            </span>
          )}
        </div>
      </div>

      <div className="mt-2 flex items-baseline gap-1 min-w-0">
        {currency && !isDisconnected && displayValue !== '—' && (
          <span className="text-xs font-semibold text-txt-muted shrink-0">{currency}</span>
        )}
        <span className={`font-bold tracking-tight tabular-nums truncate ${
          isDisconnected ? 'text-txt-muted text-base tracking-normal font-mono' : 'text-xl sm:text-2xl text-txt-primary'
        }`}>
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
