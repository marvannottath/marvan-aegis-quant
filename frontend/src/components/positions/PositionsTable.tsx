'use client';

import React, { useState } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { PortfolioPosition } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { ChevronDown, ChevronRight, XCircle, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-react';

interface PositionsTableProps {
  positions?: PortfolioPosition[];
  showCloseAction?: boolean;
}

export function PositionsTable({
  positions: customPositions,
  showCloseAction = true,
}: PositionsTableProps) {
  const { portfolio, environment, workspace, refreshData } = useTradingContext();
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [closingSymbol, setClosingSymbol] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const positions = customPositions || portfolio?.snapshot?.positions || [];
  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

  const toggleRow = (symbol: string) => {
    setExpandedRow(expandedRow === symbol ? null : symbol);
  };

  const handleClosePosition = async (sym: string) => {
    if (!confirm(`Are you sure you want to close position ${sym}?`)) return;
    try {
      setClosingSymbol(sym);
      setActionMessage(null);
      await api.closePosition(sym, environment, workspace);
      setActionMessage({ text: `Position ${sym} liquidation submitted successfully.`, type: 'success' });
      await refreshData();
    } catch (err: any) {
      setActionMessage({ text: err?.message || `Failed to close position ${sym}`, type: 'error' });
    } finally {
      setClosingSymbol(null);
    }
  };

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-brand" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            Active Broker Positions
          </h3>
          <Badge variant="neutral" size="sm">
            {positions.length} Open
          </Badge>
        </div>

        {actionMessage && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              actionMessage.type === 'success' ? 'bg-emerald-50 text-profit' : 'bg-red-50 text-loss'
            }`}
          >
            {actionMessage.text}
          </span>
        )}
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line bg-slate-50 text-txt-muted text-[11px] font-semibold uppercase tracking-wider">
              <th className="py-2.5 px-3 w-8"></th>
              <th className="py-2.5 px-3">Symbol</th>
              <th className="py-2.5 px-3">Side</th>
              <th className="py-2.5 px-3 text-right">Quantity</th>
              <th className="py-2.5 px-3 text-right">Entry</th>
              <th className="py-2.5 px-3 text-right">Current</th>
              <th className="py-2.5 px-3 text-right">Unrealized PnL</th>
              <th className="py-2.5 px-3 text-right">Exposure</th>
              <th className="py-2.5 px-3 text-center">SL / TP</th>
              <th className="py-2.5 px-3 text-center">Status</th>
              {showCloseAction && <th className="py-2.5 px-3 text-right">Action</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {positions.length === 0 ? (
              <tr>
                <td
                  colSpan={showCloseAction ? 11 : 10}
                  className="py-12 text-center text-txt-muted"
                >
                  <div className="flex flex-col items-center justify-center gap-1.5">
                    <Layers className="h-8 w-8 text-txt-subtle stroke-[1.5]" />
                    <span className="font-medium text-xs">No active positions in {workspace}</span>
                    <span className="text-[11px] text-txt-subtle">
                      Positions opened via signals or order terminal will appear here in real time.
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              positions.map((pos) => {
                const isExpanded = expandedRow === pos.symbol;
                const isProfit = pos.unrealized_pnl >= 0;
                const isBuy = pos.side === 'BUY';

                return (
                  <React.Fragment key={pos.symbol}>
                    <tr
                      onClick={() => toggleRow(pos.symbol)}
                      className="table-row-hover cursor-pointer"
                    >
                      <td className="py-2.5 px-3 text-txt-muted">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </td>
                      <td className="py-2.5 px-3 font-semibold font-mono text-txt-primary">
                        {pos.symbol}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant={isBuy ? 'success' : 'danger'} size="sm">
                          {pos.side} {pos.leverage ? `${pos.leverage}x` : ''}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                        {pos.quantity || pos.units}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                        {curr}
                        {Number(pos.entry_price).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-txt-primary">
                        {curr}
                        {Number(pos.last_price || pos.current_price).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                        <span
                          className={`inline-flex items-center gap-0.5 ${
                            isProfit ? 'text-profit' : 'text-loss'
                          }`}
                        >
                          {isProfit ? (
                            <ArrowUpRight className="h-3.5 w-3.5" />
                          ) : (
                            <ArrowDownRight className="h-3.5 w-3.5" />
                          )}
                          {isProfit ? '+' : ''}
                          {curr}
                          {Math.abs(pos.unrealized_pnl).toFixed(2)} (
                          {pos.pnl_pct ? pos.pnl_pct.toFixed(2) : '0.00'}%)
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                        {curr}
                        {Number(pos.market_value || pos.capital_allocated).toLocaleString(
                          'en-US',
                          { minimumFractionDigits: 2 }
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono text-[11px] text-txt-muted">
                        {pos.stop_loss ? `${curr}${pos.stop_loss}` : '—'} /{' '}
                        {pos.take_profit ? `${curr}${pos.take_profit}` : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant="success" size="sm">
                          {pos.status || 'ACTIVE'}
                        </Badge>
                      </td>
                      {showCloseAction && (
                        <td className="py-2.5 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => handleClosePosition(pos.symbol)}
                            disabled={closingSymbol === pos.symbol}
                            className="px-2.5 py-1 text-[11px] font-semibold rounded text-loss border border-loss/20 hover:bg-red-50 disabled:opacity-50 transition"
                          >
                            {closingSymbol === pos.symbol ? 'Closing...' : 'Close'}
                          </button>
                        </td>
                      )}
                    </tr>

                    {/* Expandable Forensic Detail Drawer */}
                    {isExpanded && (
                      <tr className="bg-slate-50/70">
                        <td colSpan={showCloseAction ? 11 : 10} className="px-6 py-3 border-t border-line">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                            <div>
                              <span className="text-txt-muted block text-[10px] uppercase">
                                Instrument ID
                              </span>
                              <span className="font-semibold text-txt-primary">
                                {pos.instrument_id || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="text-txt-muted block text-[10px] uppercase">
                                Broker Order ID
                              </span>
                              <span className="font-semibold text-txt-primary">
                                {pos.broker_position_id || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="text-txt-muted block text-[10px] uppercase">
                                Execution Exchange
                              </span>
                              <span className="font-semibold text-txt-primary">
                                {pos.exchange || 'BINANCE'}
                              </span>
                            </div>
                            <div>
                              <span className="text-txt-muted block text-[10px] uppercase">
                                Opened At
                              </span>
                              <span className="font-semibold text-txt-primary">
                                {pos.timestamp || 'N/A'}
                              </span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
