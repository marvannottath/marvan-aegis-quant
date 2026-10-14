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

// In browser execution, ALWAYS use relative path '' so requests go to current origin (e.g. https://srv1799665.hstgr.cloud)
// Never let client bundle call localhost:8000 from remote user browser
const BASE_URL = typeof window !== 'undefined'
  ? ''
  : (process.env.BACKEND_URL || 'http://127.0.0.1:8888');

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
    return fetchJson(
      `/api/performance/curve?metric=${metric}&range=${range}&environment=${env}&workspace=${ws}`
    );
  },

  async getChartHistory(
    symbol: string,
    timeframe: string = '1h',
    ws: Workspace = 'CRYPTO',
    env?: Environment
  ): Promise<{
    symbol: string;
    candles: Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }>;
    change_24h?: number;
    market_data_status?: string;
    market_data_source?: string;
    last_event_time_ist?: string;
    last_source_time_ist?: string;
    event_age_seconds?: number;
    stream_connected?: boolean;
  }> {
    const envParam = env ? `&environment=${env}` : '';
    return fetchJson(
      `/api/chart-history?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&workspace=${ws}${envParam}`
    );
  },

  async getMarketDataStatus(ws: Workspace, symbol?: string): Promise<{
    status: string;
    workspace: Workspace;
    symbol: string;
    feed_status: string;
    provider: string;
    stream_connected: boolean;
    last_event_time_ist: string;
    last_source_time_ist?: string;
    event_age_seconds: number;
    events_received: number;
    reconnect_count: number;
    latest_price: number | null;
    change_24h: number | null;
    message?: string;
  }> {
    const symParam = symbol ? `&symbol=${encodeURIComponent(symbol)}` : '';
    return fetchJson(`/api/market-data/status?workspace=${ws}${symParam}`);
  },

  // Risk & Safety
  async getRiskStatus(ws: Workspace, env?: string): Promise<RiskStatus> {
    const envParam = env ? `&environment=${env}` : '';
    const res = await fetchJson<{ status: string; data: RiskStatus }>(
      `/api/risk/status?workspace=${ws}${envParam}`
    );
    return res.data;
  },

  async setRiskProfile(profile: 'CONSERVATIVE' | 'MODERATE' | 'AGGRESSIVE', ws?: Workspace, env?: string): Promise<any> {
    return fetchJson('/api/set-risk-profile', {
      method: 'POST',
      body: JSON.stringify({ profile, workspace: ws, environment: env }),
    });
  },

  async updateRiskLimits(limits: {
    max_leverage?: number;
    stop_loss_pct?: number;
    max_open_positions?: number;
    daily_loss_limit_usd?: number;
    custom_trade_cap_usd?: number;
    circuit_breaker_drawdown_pct?: number;
    workspace?: Workspace;
    environment?: string;
  }): Promise<any> {
    return fetchJson('/api/risk/update-limits', {
      method: 'POST',
      body: JSON.stringify(limits),
    });
  },

  async resetCircuitBreaker(ws: Workspace = 'CRYPTO'): Promise<any> {
    return fetchJson('/api/risk/reset-circuit-breaker', {
      method: 'POST',
      body: JSON.stringify({ workspace: ws }),
    });
  },

  async getKillSwitchStatus(): Promise<{ is_active: boolean; message: string }> {
    return fetchJson('/api/kill-switch/status');
  },

  // AI & Autonomous Trading Controller
  async getAiStatus(): Promise<{ status: string; ai_states?: Record<string, { state: string; reason: string; user?: string; timestamp?: string; is_execution_allowed: boolean }> }> {
    return fetchJson('/api/ai/status');
  },

  async pauseAiTrading(workspace: Workspace, environment?: string): Promise<any> {
    return fetchJson('/api/ai/pause', {
      method: 'POST',
      body: JSON.stringify({ workspace, environment, reason: 'MANUAL_PAUSE', user: 'OPERATOR' }),
    });
  },

  async resumeAiTrading(workspace: Workspace, environment?: string): Promise<any> {
    return fetchJson('/api/ai/resume', {
      method: 'POST',
      body: JSON.stringify({ workspace, environment, user: 'OPERATOR' }),
    });
  },

  async triggerEmergencyKillSwitch(): Promise<any> {
    return fetchJson('/api/emergency-kill-switch/toggle', {
      method: 'POST',
      body: JSON.stringify({ confirmation_token: 'CONFIRM_KILL', action: 'ENGAGE' }),
    });
  },

  // Markets
  async getMarketScanner(ws: Workspace): Promise<{ assets: Array<{ symbol: string; price: number | null; change_24h: number | null; volume_24h?: number; rsi?: number | null; trend?: string; status?: string; source?: string; age?: string }> }> {
    return fetchJson(`/api/market-scanner?workspace=${ws}`);
  },

  // Orders & Execution
  async getOrders(env: Environment, ws?: Workspace): Promise<OrderRecord[]> {
    try {
      const wsParam = ws ? `&workspace=${ws}` : '';
      const res = await fetchJson<{ orders?: OrderRecord[] }>(`/api/orders?environment=${env}${wsParam}`);
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
    product?: string;
    leverage?: number;
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
        environment: env,
        workspace: ws,
      }),
    });
  },

  async closeAllPositions(ws: Workspace, env: Environment): Promise<any> {
    return fetchJson('/api/positions/close-all', {
      method: 'POST',
      body: JSON.stringify({
        workspace: ws,
        environment: env,
      }),
    });
  },

  async resetVault(poolName: string): Promise<any> {
    return fetchJson('/api/vault/reset', {
      method: 'POST',
      body: JSON.stringify({ pool_name: poolName }),
    });
  },

  // Vault & Ledger
  async getVaultHistory(env: Environment, ws?: Workspace): Promise<any> {
    const wsParam = ws ? `&workspace=${ws}` : '';
    return fetchJson(`/api/vault/full-history?environment=${env}${wsParam}`);
  },

  // Environment Gate Controls
  async toggleLiveTrading(enabled: boolean, token?: string, totp?: string): Promise<{ status: string; live_trading_enabled: boolean; message: string }> {
    return fetchJson('/api/toggle-live-trading', {
      method: 'POST',
      body: JSON.stringify({
        enabled,
        session_token: token,
        totp_code: totp,
      }),
    });
  },

  // Broker Gateway Management
  async getAllBrokers(env?: string, category?: string): Promise<any[]> {
    const params: string[] = [];
    if (env) params.push(`env=${encodeURIComponent(env)}`);
    if (category) params.push(`category=${encodeURIComponent(category)}`);
    const q = params.length > 0 ? `?${params.join('&')}` : '';
    const res = await fetchJson<{ status: string; brokers: any[] }>(`/api/brokers/all${q}`);
    return res.brokers || [];
  },

  async connectBroker(payload: any): Promise<any> {
    return fetchJson('/api/connect-broker', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async testBrokerConnection(payload: any): Promise<any> {
    return fetchJson('/api/test-broker-connection', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async disconnectBroker(brokerId: string): Promise<any> {
    return fetchJson('/api/disconnect-broker', {
      method: 'POST',
      body: JSON.stringify({ broker_id: brokerId }),
    });
  },

  // Vault Sweep to Binance Spot / Funding
  async sweepToBinanceFunding(amount?: number): Promise<any> {
    return fetchJson('/api/vault/sweep-to-binance-funding', {
      method: 'POST',
      body: JSON.stringify({ amount: amount || 0 }),
    });
  },

  // Universal Broker-Aware Vault Sweep
  async sweepVault(payload: { workspace: Workspace; environment: string; amount?: number }): Promise<any> {
    return fetchJson('/api/vault/sweep', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async toggleAutoSweep(enabled?: boolean): Promise<{ status: string; auto_sweep_enabled: boolean; message: string }> {
    return fetchJson('/api/vault/toggle-auto-sweep', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  },

  async getAutoSweepStatus(): Promise<{ auto_sweep_enabled: boolean; sweep_percentage: number; min_sweep_amount_usd: number }> {
    return fetchJson('/api/vault/auto-sweep-status');
  },

  // Monthly PnL Calendar Heatmap
  async getPnlCalendar(month?: string, workspace: string = 'ALL', environment?: string): Promise<any> {
    const params = new URLSearchParams();
    if (month) params.set('month', month);
    if (workspace) params.set('workspace', workspace);
    if (environment) params.set('environment', environment);
    const q = params.toString() ? `?${params.toString()}` : '';
    return fetchJson(`/api/analytics/pnl-calendar${q}`);
  },

  // CA Tax Audit & Investor Factsheet
  async getTaxAudit(): Promise<any> {
    return fetchJson('/api/reports/tax-audit');
  },

  async getFactsheet(): Promise<any> {
    return fetchJson('/api/reports/factsheet');
  },

  // AI Auto-Tuner & Walk-Forward Optimizer
  async getOptimizerStatus(): Promise<any> {
    return fetchJson('/api/optimizer/status');
  },

  async runOptimizer(workspace: string = 'CRYPTO'): Promise<any> {
    return fetchJson('/api/optimizer/run', {
      method: 'POST',
      body: JSON.stringify({ workspace }),
    });
  },

  // Advanced Strategies Catalog
  async getStrategiesCatalog(): Promise<any> {
    return fetchJson('/api/strategies/catalog');
  },

  async toggleStrategy(strategyId: string, enabled: boolean): Promise<any> {
    return fetchJson('/api/strategies/toggle', {
      method: 'POST',
      body: JSON.stringify({ strategy_id: strategyId, enabled }),
    });
  },

  // Super Admin Endpoints
  async adminLogin(password: string, username: string = 'marvan', totpCode?: string): Promise<any> {
    return fetchJson('/api/admin/login', {
      method: 'POST',
      body: JSON.stringify({
        username,
        password,
        totp_code: totpCode || '',
      }),
    });
  },

  async getAdminOverview(token: string): Promise<any> {
    return fetchJson('/api/admin/overview', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  async getAdminUsers(token: string): Promise<any> {
    return fetchJson('/api/admin/users', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  async createAdminUser(token: string, payload: any): Promise<any> {
    return fetchJson('/api/admin/create-user', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
  },

  async updateAdminUser(token: string, payload: any): Promise<any> {
    return fetchJson('/api/admin/update-user', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
  },

  async deleteAdminUser(token: string, username: string): Promise<any> {
    return fetchJson('/api/admin/delete-user', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ username }),
    });
  },

  async requestPasswordReset(username: string): Promise<any> {
    return fetchJson('/api/admin/request-otp', {
      method: 'POST',
      body: JSON.stringify({ username }),
    });
  },

  async verifyResetToken(email: string, token: string): Promise<any> {
    return fetchJson('/api/admin/verify-reset-token', {
      method: 'POST',
      body: JSON.stringify({ email, token }),
    });
  },

  async resetPasswordWithToken(email: string, token: string, newPassword: string): Promise<any> {
    return fetchJson('/api/admin/reset-password-with-token', {
      method: 'POST',
      body: JSON.stringify({ email, token, new_password: newPassword }),
    });
  },

  async verifyOtpReset(email: string, otp: string, newPassword: string): Promise<any> {
    return fetchJson('/api/admin/verify-otp-reset', {
      method: 'POST',
      body: JSON.stringify({ email, otp, new_password: newPassword }),
    });
  },

  async getTotpSetup(username: string): Promise<any> {
    return fetchJson(`/api/auth/totp-setup/${encodeURIComponent(username)}`);
  },

  async activateTotp(username: string, code: string): Promise<any> {
    return fetchJson('/api/auth/totp-activate', {
      method: 'POST',
      body: JSON.stringify({ username, code }),
    });
  },

  async deactivateTotp(token: string, username: string): Promise<any> {
    return fetchJson('/api/auth/totp-deactivate', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ username, session_token: token }),
    });
  },

  async resetTotp(username: string): Promise<any> {
    return fetchJson('/api/auth/totp-reset', {
      method: 'POST',
      body: JSON.stringify({ username }),
    });
  },

  async resetPasswordDirect(username: string, newPassword: string): Promise<any> {
    return fetchJson('/api/auth/reset-password-direct', {
      method: 'POST',
      body: JSON.stringify({ username, new_password: newPassword }),
    });
  },

  async changePassword(token: string, oldPassword: string, newPassword: string): Promise<any> {
    return fetchJson('/api/auth/change-password', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },
};

export function getWebSocketUrl(workspace?: string, environment?: string): string {
  if (typeof window === 'undefined') return '';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let host = window.location.host;
  // If running locally in browser (port 3000), connect directly to FastAPI backend on port 8888
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    host = `${window.location.hostname}:8888`;
  }
  let url = `${protocol}//${host}/ws`;
  const params: string[] = [];
  if (workspace) params.push(`workspace=${encodeURIComponent(workspace)}`);
  if (environment) params.push(`environment=${encodeURIComponent(environment)}`);
  if (params.length > 0) url += `?${params.join('&')}`;
  return url;
}

