import {
  AccountContext,
  PortfolioAggregate,
  CapitalBreakdown,
  RiskStatus,
  AISignal,
  EnvironmentStatus,
  Environment,
  Workspace,
  OrderRecord,
} from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text();
    let errorMessage = `API Error ${res.status}: ${res.statusText}`;
    try {
      const parsed = JSON.parse(errorText);
      errorMessage = parsed.message || parsed.reason || errorMessage;
    } catch {
      // Keep fallback
    }
    throw new Error(errorMessage);
  }

  return res.json();
}

export const api = {
  // Authoritative Context
  async getAccountContext(env: Environment, ws: Workspace): Promise<AccountContext> {
    const res = await fetchJson<{ status: string; account_context: AccountContext }>(
      `/api/account/context?environment=${env}&workspace=${ws}`
    );
    return res.account_context;
  },

  async getEnvironmentStatus(): Promise<EnvironmentStatus> {
    const res = await fetchJson<{ status: string; data: EnvironmentStatus }>(
      '/api/environment/status'
    );
    return res.data;
  },

  // Financial Engines & Single Sources of Truth
  async getPortfolioAggregate(env: Environment, ws: Workspace): Promise<PortfolioAggregate> {
    return fetchJson<PortfolioAggregate>(
      `/api/portfolio/aggregate?environment=${env}&workspace=${ws}`
    );
  },

  async getCapitalBreakdown(env: Environment, ws: Workspace): Promise<CapitalBreakdown> {
    const res = await fetchJson<{ status: string; breakdown: CapitalBreakdown }>(
      `/api/capital/breakdown?environment=${env}&workspace=${ws}`
    );
    return res.breakdown;
  },

  async getPerformanceCurve(
    metric: 'equity' | 'pnl' | 'drawdown',
    range: '1D' | '1W' | '1M' | '3M' | 'ALL',
    env: Environment,
    ws: Workspace
  ): Promise<{ points: Array<{ timestamp: string; value: number }>; metric: string; range: string }> {
    const envParam = env === 'LIVE' ? 'BINANCE_LIVE_REAL' : 'BINANCE_TESTNET_DEMO';
    return fetchJson(
      `/api/performance/curve?metric=${metric}&time_range=${range}&environment=${envParam}&workspace=${ws}`
    );
  },

  async getChartHistory(
    symbol: string,
    timeframe: string = '1h',
    ws: Workspace = 'CRYPTO',
    env?: Environment
  ): Promise<{ symbol: string; candles: Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }> }> {
    const envParam = env ? `&environment=${env}` : '';
    return fetchJson(
      `/api/chart-history?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&workspace=${ws}${envParam}`
    );
  },

  // Risk & Safety
  async getRiskStatus(ws: Workspace): Promise<RiskStatus> {
    const res = await fetchJson<{ status: string; data: RiskStatus }>(
      `/api/risk/status?workspace=${ws}`
    );
    return res.data;
  },

  async getKillSwitchStatus(): Promise<{ is_active: boolean; message: string }> {
    return fetchJson('/api/kill-switch/status');
  },

  // AI & Signals
  async getAiStatus(): Promise<{ status: string; signals?: AISignal[]; active_model?: string; confidence_threshold?: number }> {
    return fetchJson('/api/ai/status');
  },

  // Markets
  async getMarketScanner(ws: Workspace): Promise<{ assets: Array<{ symbol: string; price: number; change_24h: number; volume_24h: number; rsi: number; trend: string }> }> {
    return fetchJson(`/api/market-scanner?workspace=${ws}`);
  },

  // Orders & Execution
  async getOrders(env: Environment): Promise<OrderRecord[]> {
    try {
      const res = await fetchJson<{ orders?: OrderRecord[] }>(`/api/orders?environment=${env}`);
      return res.orders || [];
    } catch {
      return [];
    }
  },

  async submitOrder(order: {
    symbol: string;
    side: 'BUY' | 'SELL';
    quantity: number;
    price?: number;
    order_type?: string;
    environment: string;
    workspace: Workspace;
  }): Promise<{ status: string; internal_order_id?: string; message?: string }> {
    return fetchJson('/api/orders/submit', {
      method: 'POST',
      body: JSON.stringify(order),
    });
  },

  async closePosition(symbol: string, env: Environment, ws: Workspace): Promise<any> {
    return fetchJson('/api/close-position', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        environment: env === 'LIVE' ? 'BINANCE_LIVE' : 'BINANCE_TESTNET',
        workspace: ws,
      }),
    });
  },

  // Vault & Ledger
  async getVaultHistory(env: Environment): Promise<any> {
    const envParam = env === 'LIVE' ? 'BINANCE_LIVE_REAL' : 'BINANCE_TESTNET_DEMO';
    return fetchJson(`/api/vault/full-history?environment=${envParam}`);
  },

  // Environment Gate Controls
  async toggleLiveTrading(enabled: boolean): Promise<{ status: string; live_trading_enabled: boolean; message: string }> {
    return fetchJson('/api/toggle-live-trading', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  },
};

export function getWebSocketUrl(workspace?: string, environment?: string): string {
  if (typeof window === 'undefined') return '';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  let url = `${protocol}//${host}/ws`;
  const params: string[] = [];
  if (workspace) params.push(`workspace=${encodeURIComponent(workspace)}`);
  if (environment) params.push(`environment=${encodeURIComponent(environment)}`);
  if (params.length > 0) url += `?${params.join('&')}`;
  return url;
}

