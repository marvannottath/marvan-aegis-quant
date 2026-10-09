'use client';

import React from 'react';
import { OrdersTable } from '../../components/orders/OrdersTable';

export default function OrdersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Orders Terminal
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Full order lifecycle execution logs, status transitions, and fees.
          </p>
        </div>
      </div>
      <OrdersTable />
    </div>
  );
}
