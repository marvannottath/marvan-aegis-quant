'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  Environment,
  Workspace,
  AccountContext,
  PortfolioAggregate,
  CapitalBreakdown,
  EnvironmentStatus,
} from '../lib/types';
import { api } from '../lib/api';

interface TradingContextValue {
  environment: Environment;
  workspace: Workspace;
  account: AccountContext | null;
  portfolio: PortfolioAggregate | null;
  capital: CapitalBreakdown | null;
  envStatus: EnvironmentStatus | null;
  isLoading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  switchEnvironment: (targetEnv: Environment) => void;
  switchWorkspace: (targetWs: Workspace) => void;
}

const TradingContext = createContext<TradingContextValue | null>(null);

export function TradingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  // 1. Authoritative Environment derivation from pathname
  const environment: Environment = useMemo(() => {
    return pathname.startsWith('/demo') ? 'DEMO' : 'LIVE';
  }, [pathname]);

  // 2. Authoritative Workspace derivation from pathname
  const workspace: Workspace = useMemo(() => {
    const clean = pathname.replace(/^\/demo/, '');
    if (clean.includes('/india')) return 'INDIA';
    if (clean.includes('/forex-gold')) return 'FOREX_GOLD';
    return 'CRYPTO'; // Standard institutional default workspace
  }, [pathname]);

  // Client State
  const [account, setAccount] = useState<AccountContext | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioAggregate | null>(null);
  const [capital, setCapital] = useState<CapitalBreakdown | null>(null);
  const [envStatus, setEnvStatus] = useState<EnvironmentStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Authoritative State Refresh
  const refreshData = useCallback(async () => {
    try {
      setError(null);
      const [acc, port, cap, envSt] = await Promise.allSettled([
        api.getAccountContext(environment, workspace),
        api.getPortfolioAggregate(environment, workspace),
        api.getCapitalBreakdown(environment, workspace),
        api.getEnvironmentStatus(),
      ]);

      if (acc.status === 'fulfilled') setAccount(acc.value);
      if (port.status === 'fulfilled') setPortfolio(port.value);
      if (cap.status === 'fulfilled') setCapital(cap.value);
      if (envSt.status === 'fulfilled') setEnvStatus(envSt.value);
    } catch (err: any) {
      setError(err?.message || 'Failed to load trading context');
    } finally {
      setIsLoading(false);
    }
  }, [environment, workspace]);

  // Clean state flush and reload when environment or workspace changes
  useEffect(() => {
    setIsLoading(true);
    setAccount(null);
    setPortfolio(null);
    setCapital(null);
    refreshData();

    // High-frequency polling (3 seconds) for live trading telemetry
    const interval = setInterval(refreshData, 3000);
    return () => clearInterval(interval);
  }, [environment, workspace, refreshData]);

  // Switch Environment: STRICTLY PRESERVES WORKSPACE & SUBPATH
  const switchEnvironment = useCallback((targetEnv: Environment) => {
    if (targetEnv === environment) return;

    // Flush client state first
    setAccount(null);
    setPortfolio(null);
    setCapital(null);
    setIsLoading(true);

    let nextPath: string;
    if (targetEnv === 'DEMO') {
      // LIVE -> DEMO: prepend /demo
      if (pathname === '/') {
        nextPath = '/demo';
      } else {
        nextPath = `/demo${pathname}`;
      }
    } else {
      // DEMO -> LIVE: remove /demo prefix
      nextPath = pathname.replace(/^\/demo/, '') || '/';
    }

    router.push(nextPath);
  }, [environment, pathname, router]);

  // Switch Workspace: PRESERVES ENVIRONMENT
  const switchWorkspace = useCallback((targetWs: Workspace) => {
    if (targetWs === workspace) return;

    // Flush client state first
    setAccount(null);
    setPortfolio(null);
    setCapital(null);
    setIsLoading(true);

    const isDemo = environment === 'DEMO';
    const wsSlug = targetWs === 'CRYPTO' ? 'crypto' : (targetWs === 'INDIA' ? 'india' : 'forex-gold');

    // If on a sub-section page (e.g. /positions or /orders), stay on that page or navigate to workspace view
    const isSubpage = ['/positions', '/orders', '/risk', '/portfolio', '/analytics', '/signals', '/settings'].some(
      sub => pathname.endsWith(sub)
    );

    let nextPath: string;
    if (isSubpage) {
      // keep current page
      nextPath = pathname;
    } else {
      nextPath = isDemo ? `/demo/${wsSlug}` : `/${wsSlug}`;
    }

    router.push(nextPath);
  }, [environment, workspace, pathname, router]);

  const value = useMemo(
    () => ({
      environment,
      workspace,
      account,
      portfolio,
      capital,
      envStatus,
      isLoading,
      error,
      refreshData,
      switchEnvironment,
      switchWorkspace,
    }),
    [environment, workspace, account, portfolio, capital, envStatus, isLoading, error, refreshData, switchEnvironment, switchWorkspace]
  );

  return <TradingContext.Provider value={value}>{children}</TradingContext.Provider>;
}

export function useTradingContext() {
  const context = useContext(TradingContext);
  if (!context) {
    throw new Error('useTradingContext must be used within a TradingProvider');
  }
  return context;
}
