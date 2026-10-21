'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { OrderRecord } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import {
  BarChart3,
  RefreshCw,
  Clock,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';

interface OrdersTableProps {
  initialPageSize?: number;
}

export function OrdersTable({ initialPageSize = 10 }: OrdersTableProps) {
  const { environment, workspace, portfolio } = useTradingContext();

  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Pagination states
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(initialPageSize);

  const curr = portfolio?.currency_symbol || '$';
  const isLiveDisconnected =
    environment === 'LIVE' &&
    (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);

  const loadOrders = useCallback(async () => {
    try {
      setIsLoading(true);
      const offset = (currentPage - 1) * pageSize;
      const res = await api.getOrders(environment, workspace, pageSize, offset, filterStatus);
      setOrders(res.orders);
      setTotalCount(res.total_count);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setIsLoading(false);
    }
  }, [environment, workspace, currentPage, pageSize, filterStatus]);

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 8000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  // Reset to page 1 when filter or workspace changes
  const handleFilterChange = (status: string) => {
    setFilterStatus(status);
    setCurrentPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startIndex = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(totalCount, currentPage * pageSize);

  const statusFilters = [
    'ALL',
    'OPEN',
    'FILLED',
    'PARTIALLY_FILLED',
    'PENDING',
    'CANCELLED',
    'FAILED',
  ];

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
    <div id="orders-section" className="card-panel overflow-hidden flex flex-col scroll-mt-20 border border-line rounded-xl bg-panel shadow-2xs">
      {/* Header & Status Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line bg-slate-50/50 dark:bg-panel-light/30">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-brand" />
          <h3
            className="text-xs font-bold uppercase tracking-wider text-txt-primary"
            title="Immutable audit log of all market executions, broker transitions, and order lifecycle events"
          >
            Order Execution History & Terminal
          </h3>
          <span className="text-xs font-mono font-semibold text-brand px-1.5 py-0.5 bg-blue-50 dark:bg-blue-950/40 border border-brand/20 rounded">
            {totalCount} Audited
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-white dark:bg-panel p-0.5 rounded-lg border border-line">
            {statusFilters.map((st) => (
              <button
                key={st}
                onClick={() => handleFilterChange(st)}
                className={`px-2 py-0.5 text-[11px] font-semibold rounded transition cursor-pointer ${
                  filterStatus === st
                    ? 'bg-slate-900 dark:bg-brand text-white shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={() => loadOrders()}
            className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-100 dark:hover:bg-panel rounded-lg border border-line transition cursor-pointer"
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
            <tr className="border-b border-line bg-slate-50 dark:bg-panel-light/50 text-txt-muted text-[11px] font-semibold uppercase tracking-wider">
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
            {orders.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-txt-muted">
                  <div className="flex flex-col items-center justify-center gap-2 max-w-sm mx-auto">
                    <Clock className="h-8 w-8 text-txt-subtle stroke-[1.5]" />
                    <span className="font-bold text-xs text-txt-primary">
                      {isLiveDisconnected
                        ? 'Live Broker Not Connected'
                        : `No orders found (${filterStatus})`}
                    </span>
                    <span className="text-[11px] text-txt-muted leading-relaxed">
                      {isLiveDisconnected
                        ? 'Zero active live orders. Simulated paper orders are strictly isolated from the Live desk.'
                        : 'Authoritative order state machine tracks all lifecycle transitions in real-time.'}
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              orders.map((ord) => {
                const isBuy = ord.side === 'BUY';
                return (
                  <tr key={ord.order_id} className="hover:bg-slate-50/60 dark:hover:bg-panel-light/40 transition">
                    <td className="py-2 px-3 font-mono text-[11px] font-semibold text-txt-primary">
                      {ord.order_id}
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px] text-txt-muted">
                      {ord.created_at || 'Just now'}
                    </td>
                    <td className="py-2 px-3 font-mono font-semibold text-txt-primary">
                      {ord.symbol}
                    </td>
                    <td className="py-2 px-3">
                      <Badge variant={isBuy ? 'success' : 'danger'} size="sm">
                        {ord.side}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 font-mono text-txt-secondary text-[11px]">
                      {ord.order_type || 'MARKET'}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums text-txt-secondary">
                      {ord.quantity}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums text-txt-secondary">
                      {ord.price > 0 ? `${curr}${ord.price.toFixed(2)}` : 'MARKET'}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-txt-primary">
                      {ord.fill_qty > 0 ? ord.fill_qty : '0.00'}
                    </td>
                    <td className="py-2 px-3 text-center">
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

      {/* ── PAGINATION CONTROLS BAR (Eliminates Heavy Loading) ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-line bg-slate-50/40 dark:bg-panel-light/20 text-xs">
        <div className="flex items-center gap-2 text-txt-muted">
          <span>
            Showing <strong className="text-txt-primary">{startIndex}</strong> -{' '}
            <strong className="text-txt-primary">{endIndex}</strong> of{' '}
            <strong className="text-txt-primary">{totalCount}</strong> orders
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">
            Page <strong className="text-txt-primary">{currentPage}</strong> of{' '}
            <strong className="text-txt-primary">{totalPages}</strong>
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Rows per page dropdown */}
          <div className="flex items-center gap-1.5 text-txt-muted text-[11px]">
            <span>Rows:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-panel border border-line rounded px-2 py-1 text-xs text-txt-primary focus:outline-none"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          {/* Navigation buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage <= 1 || isLoading}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="First Page"
            >
              <ChevronsLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1 || isLoading}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Previous Page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <span className="px-2 py-0.5 font-mono text-xs font-semibold text-txt-primary bg-panel border border-line rounded">
              {currentPage} / {totalPages}
            </span>

            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages || isLoading}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Next Page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage >= totalPages || isLoading}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
              title="Last Page"
            >
              <ChevronsRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
