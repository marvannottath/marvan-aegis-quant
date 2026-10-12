'use client';

import React, { Suspense } from 'react';
import { SessionDetailView } from '../../../../components/analytics/SessionDetailView';
import { RefreshCw } from 'lucide-react';

export default function DemoAnalyticsSessionPage() {
  return (
    <Suspense
      fallback={
        <div className="py-24 text-center text-txt-muted flex flex-col items-center justify-center gap-2">
          <RefreshCw className="w-6 h-6 animate-spin text-brand" />
          <span>Loading session analytics...</span>
        </div>
      }
    >
      <SessionDetailView />
    </Suspense>
  );
}
