'use client';

import React from 'react';
import { OrdersTable } from '../../../components/orders/OrdersTable';

export default function DemoOrdersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Orders Terminal (DEMO)
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Paper & Testnet simulated order submissions and executions.
          </p>
        </div>
      </div>
      <OrdersTable />
    </div>
  );
}
