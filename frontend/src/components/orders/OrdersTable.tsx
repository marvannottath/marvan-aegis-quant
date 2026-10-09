'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { OrderRecord } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { BarChart3, RefreshCw, Clock } from 'lucide-react';

export function OrdersTable() {
  const { environment, workspace, portfolio } = useTradingContext();
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  const curr = portfolio?.currency_symbol || '$';

  const loadOrders = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.getOrders(environment);
      setOrders(data);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setIsLoading(false);
    }
  }, [environment]);

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 4000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  const statusFilters = [
    'ALL',
    'OPEN',
    'FILLED',
    'PARTIALLY_FILLED',
    'PENDING',
    'CANCELLED',
    'FAILED',
  ];

  const filteredOrders = orders.filter((o) => {
    if (filterStatus === 'ALL') return true;
    if (filterStatus === 'OPEN') {
      return ['CREATED', 'RISK_PENDING', 'APPROVED', 'SUBMITTED', 'ACKNOWLEDGED'].includes(
        o.status
      );
    }
    return o.status === filterStatus;
  });

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'FILLED':
        return 'success';
      case 'PARTIALLY_FILLED':
      case 'APPROVED':
      case 'SUBMITTED':
      case 'ACKNOWLEDGED':
        return 'info';
      case 'FAILED':
        return 'danger';
      case 'CANCELLED':
        return 'neutral';
      case 'RISK_PENDING':
      case 'CREATED':
      default:
        return 'warning';
    }
  };

  return (
    <div className="card-panel overflow-hidden flex flex-col">
      {/* Header & Status Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line bg-slate-50/50">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-brand" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            Orders Terminal
          </h3>
          <span className="text-xs font-mono text-txt-muted">
            ({orders.length} total)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-white p-0.5 rounded border border-line">
            {statusFilters.map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-2 py-0.5 text-[11px] font-semibold rounded transition ${
                  filterStatus === st
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={() => loadOrders()}
            className="p-1 text-txt-muted hover:text-txt-primary hover:bg-slate-100 rounded transition"
            title="Refresh orders"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Orders Data Grid */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line bg-slate-50 text-txt-muted text-[11px] font-semibold uppercase tracking-wider">
              <th className="py-2.5 px-3">Order ID</th>
              <th className="py-2.5 px-3">Time</th>
              <th className="py-2.5 px-3">Symbol</th>
              <th className="py-2.5 px-3">Side</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3 text-right">Quantity</th>
              <th className="py-2.5 px-3 text-right">Price</th>
              <th className="py-2.5 px-3 text-right">Filled</th>
              <th className="py-2.5 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {filteredOrders.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-txt-muted">
                  <div className="flex flex-col items-center justify-center gap-1.5">
                    <Clock className="h-8 w-8 text-txt-subtle stroke-[1.5]" />
                    <span className="font-medium text-xs">No orders found for filter: {filterStatus}</span>
                    <span className="text-[11px] text-txt-subtle">
                      Authoritative order state machine tracks all lifecycle states.
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              filteredOrders.map((ord) => {
                const isBuy = ord.side === 'BUY';
                return (
                  <tr key={ord.order_id} className="table-row-hover">
                    <td className="py-2.5 px-3 font-mono text-[11px] font-semibold text-txt-primary">
                      {ord.order_id}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-txt-muted">
                      {ord.created_at || 'Just now'}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-txt-primary">
                      {ord.symbol}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant={isBuy ? 'success' : 'danger'} size="sm">
                        {ord.side}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-txt-secondary">
                      {ord.order_type || 'MARKET'}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                      {ord.quantity}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                      {ord.price > 0 ? `${curr}${ord.price.toFixed(2)}` : 'MARKET'}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-txt-primary">
                      {ord.fill_qty > 0 ? ord.fill_qty : '0.00'}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <Badge variant={getStatusBadgeVariant(ord.status)} size="sm">
                        {ord.status}
                      </Badge>
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
