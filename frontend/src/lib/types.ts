export type Environment = 'LIVE' | 'DEMO';
export type Workspace = 'CRYPTO' | 'INDIA' | 'FOREX_GOLD';

export interface AccountContext {
  account_id: string;
  workspace: Workspace;
  environment: 'LIVE' | 'PAPER';
  broker: string;
  currency: string;
  currency_symbol: string;
  instruments: string[];
  risk_profile: 'CONSERVATIVE' | 'MODERATE' | 'AGGRESSIVE';
  capabilities: {
    spot: boolean;
    futures: boolean;
    auto_trading: boolean;
    vault: boolean;
    news: boolean;
    backtest: boolean;
    reports: boolean;
    withdrawals: boolean;
  };
  account_status: string;
  initial_capital: number;
  created_at: string;
  metadata?: Record<string, any>;
  mode: Environment;
  permissions: string[];
}

export interface PortfolioPosition {
  workspace: Workspace;
  symbol: string;
  instrument_id: string;
  exchange: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  units: number;
  entry_price: number;
  last_price: number;
  current_price: number;
  market_value: number;
  capital_allocated: number;
  margin: number;
  unrealized_pnl: number;
  pnl_usd: number;
  pnl_pct: number;
  product: string;
  leverage: number;
  stop_loss?: number;
  take_profit?: number;
  timestamp: string;
  status: string;
  broker_position_id?: string;
}

export interface PortfolioAggregate {
  status: string;
  workspace: Workspace;
  pool_name: string;
  currency: string;
  currency_symbol: string;
  total_equity: number | null;
  free_cash: number | null;
  broker_connected?: boolean;
  data_source?: string;
  is_simulated?: boolean;
  provenance?: string;
  error_code?: string;
  open_positions: number;
  open_positions_count: number;
  exposure: number;
  total_exposure: number;
  used_margin: number;
  available_margin: number;
  unrealized_pnl: number;
  realized_pnl: number;
  vault_balance: number;
  initial_capital: number;
  peak_equity: number;
  drawdown_pct: number;
  daily_opening_equity: number;
  daily_drawdown_pct: number;
  reconciliation_status: string;
  snapshot?: {
    positions: PortfolioPosition[];
    delta_detected: boolean;
    delta_description: string;
    broker_sync: string;
  };
}

export interface CapitalBreakdown {
  account_id: string;
  currency: string;
  total_equity: number | null;
  broker_balance: number | null;
  available_cash: number | null;
  reserved_cash: number;
  used_margin: number;
  open_orders_reserved: number;
  residual_dust_capital: number;
  safety_buffer: number;
  tradeable_capital: number | null;
  can_open_new_trades: boolean;
  residual_assets: Array<{
    symbol: string;
    quantity: number;
    notional_value: number;
    status: string;
    reason: string;
  }>;
}

export interface OrderRecord {
  order_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  order_type: 'MARKET' | 'LIMIT';
  environment: string;
  strategy?: string;
  status: 'CREATED' | 'RISK_PENDING' | 'APPROVED' | 'SUBMITTED' | 'ACKNOWLEDGED' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'FAILED' | 'PENDING_VERIFICATION';
  fill_qty: number;
  avg_fill_price: number;
  fees?: number;
  created_at: string;
  updated_at: string;
  transitions?: Array<{ from: string | null; to: string; at: string; reason: string }>;
}

export interface RiskStatus {
  active_profile_name: string;
  max_drawdown_pct: number;
  daily_loss_limit_usd: number;
  daily_realized_loss: number;
  custom_trade_cap_usd: number;
  circuit_tripped: boolean;
  trip_reason: string;
  max_leverage: number;
  max_open_positions: number;
  stop_loss_pct: number;
  workspace_daily_loss_limit?: number;
}

export interface AISignal {
  signal_id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  model: string;
  market_regime: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward_ratio: number;
  timestamp: string;
  status: string;
}

export interface EnvironmentStatus {
  paper_trading: string;
  binance_testnet: string;
  live_trading: string;
  live_withdrawals: string;
  stripe_live: string;
  live_trading_enabled_flag: boolean;
  live_withdrawals_enabled_flag: boolean;
  kill_switch_active: boolean;
  reconciliation_status: string;
  stale_threshold_seconds: number;
}
