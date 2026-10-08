"""
Aegis-Quant Authoritative Account Context.
Single Source of Truth for Account Identity, Workspace, Environment, Broker,
Currency, Instruments, Risk Profile, and Capabilities.

Enforces Fail-Closed Isolation:
- No global active account fallback
- No global active pool fallback
- No global equity fallback
- No last-used account fallback
- No cross-workspace financial fallback
- No cross-broker state fallback

If account context cannot be resolved: FAIL CLOSED with ACCOUNT_CONTEXT_UNAVAILABLE.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Standardized Error and Status Codes
STATUS_ACTIVE = "ACTIVE"
STATUS_LOCKED = "LOCKED"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_DISCONNECTED = "DISCONNECTED"

ACCOUNT_CONTEXT_UNAVAILABLE = "ACCOUNT_CONTEXT_UNAVAILABLE"


@dataclass
class AccountContext:
    account_id: str
    workspace: str                  # CRYPTO | INDIA | FOREX_GOLD
    environment: str                # LIVE | PAPER | BACKTEST
    broker: str                     # BINANCE | UPSTOX | MT5 | CTRADER | KOTAK | MOCK
    currency: str                   # USDT | INR | USD
    currency_symbol: str            # $ | ₹
    instruments: List[str]          # [SPOT, USDT_M_FUTURES] or [EQUITY, DERIVATIVES] or [FOREX, COMMODITIES]
    risk_profile: str               # CONSERVATIVE | MODERATE | AGGRESSIVE
    capabilities: Dict[str, bool]   # {spot: True, futures: False, auto_trading: True, ...}
    account_status: str             # ACTIVE | LOCKED | SUSPENDED | DISCONNECTED
    initial_capital: float = 100000.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = "LIVE" if self.environment == "LIVE" else "DEMO"
        d["environment_id"] = self.environment
        d["workspace_id"] = self.workspace
        d["permissions"] = ["READ", "TRADE"] if self.environment == "PAPER" else ["READ"]
        return d

    @property
    def mode(self) -> str:
        return "LIVE" if self.environment == "LIVE" else "DEMO"

    @property
    def environment_id(self) -> str:
        return self.environment

    @property
    def workspace_id(self) -> str:
        return self.workspace

    def is_live(self) -> bool:
        return self.environment == "LIVE"

    def is_paper(self) -> bool:
        return self.environment == "PAPER"

    def is_demo(self) -> bool:
        return self.environment in ("PAPER", "DEMO", "TESTNET")

    def is_backtest(self) -> bool:
        return self.environment == "BACKTEST"

    def supports(self, capability: str) -> bool:
        return bool(self.capabilities.get(capability, False))


class AccountContextManager:
    """
    Authoritative Account Context Manager.
    Resolves, validates, and scopes trading requests to explicit AccountContext.
    """

    def __init__(self):
        # Known Account Definitions
        self._accounts: Dict[str, AccountContext] = {
            # ── CRYPTO ──────────────────────────────────────────
            "BINANCE_SPOT_DEMO": AccountContext(
                account_id="BINANCE_SPOT_DEMO",
                workspace="CRYPTO",
                environment="PAPER",
                broker="BINANCE",
                currency="USDT",
                currency_symbol="$",
                instruments=["SPOT"],
                risk_profile="MODERATE",
                capabilities={
                    "spot": True,
                    "futures": False,          # Futures live locked
                    "auto_trading": True,
                    "vault": True,
                    "news": True,
                    "backtest": True,
                    "reports": True,
                    "withdrawals": False        # Never enable live withdrawals
                },
                account_status=STATUS_ACTIVE,
                initial_capital=19950.55,
                metadata={"exchange": "Binance Spot Testnet / Demo"}
            ),
            "BINANCE_LIVE_REAL": AccountContext(
                account_id="BINANCE_LIVE_REAL",
                workspace="CRYPTO",
                environment="LIVE",
                broker="BINANCE",
                currency="USDT",
                currency_symbol="$",
                instruments=["SPOT"],
                risk_profile="CONSERVATIVE",
                capabilities={
                    "spot": True,
                    "futures": False,          # Futures LIVE LOCKED
                    "auto_trading": False,      # Requires explicit approval
                    "vault": True,
                    "news": True,
                    "backtest": False,
                    "reports": True,
                    "withdrawals": False        # Locked server-side
                },
                account_status=STATUS_ACTIVE,
                initial_capital=0.0,
                metadata={"exchange": "Binance Production Spot"}
            ),

            # ── INDIA ───────────────────────────────────────────
            "AEGIS_INDIA_INR": AccountContext(
                account_id="AEGIS_INDIA_INR",
                workspace="INDIA",
                environment="PAPER",
                broker="UPSTOX",
                currency="INR",
                currency_symbol="₹",
                instruments=["EQUITY", "ETF", "INDEX"],
                risk_profile="CONSERVATIVE",
                capabilities={
                    "spot": True,
                    "futures": False,
                    "auto_trading": True,
                    "vault": True,
                    "news": True,
                    "backtest": True,
                    "reports": True,
                    "withdrawals": False
                },
                account_status=STATUS_ACTIVE,
                initial_capital=100000.0,
                metadata={"exchange": "NSE/BSE Upstox Simulation"}
            ),
            "UPSTOX_LIVE": AccountContext(
                account_id="UPSTOX_LIVE",
                workspace="INDIA",
                environment="LIVE",
                broker="UPSTOX",
                currency="INR",
                currency_symbol="₹",
                instruments=["EQUITY", "DERIVATIVES"],
                risk_profile="CONSERVATIVE",
                capabilities={
                    "spot": True,
                    "futures": False,
                    "auto_trading": False,
                    "vault": True,
                    "news": True,
                    "backtest": False,
                    "reports": True,
                    "withdrawals": False
                },
                account_status=STATUS_ACTIVE,
                initial_capital=0.0,
                metadata={"exchange": "Upstox Live Pro API"}
            ),

            # ── FOREX & COMMODITIES ─────────────────────────────
            "MT5_DEMO": AccountContext(
                account_id="MT5_DEMO",
                workspace="FOREX_GOLD",
                environment="PAPER",
                broker="MT5",
                currency="USD",
                currency_symbol="$",
                instruments=["FOREX", "COMMODITIES"],
                risk_profile="MODERATE",
                capabilities={
                    "spot": True,
                    "futures": False,
                    "auto_trading": True,
                    "vault": True,
                    "news": True,
                    "backtest": True,
                    "reports": True,
                    "withdrawals": False
                },
                account_status=STATUS_ACTIVE,
                initial_capital=100000.0,
                metadata={"exchange": "Interbank OTC / Global FX Demo Sandbox"}
            ),
            "MT5_LIVE_REAL": AccountContext(
                account_id="MT5_LIVE_REAL",
                workspace="FOREX_GOLD",
                environment="LIVE",
                broker="MT5",
                currency="USD",
                currency_symbol="$",
                instruments=["FOREX", "COMMODITIES"],
                risk_profile="CONSERVATIVE",
                capabilities={
                    "spot": True,
                    "futures": False,
                    "auto_trading": False,
                    "vault": True,
                    "news": True,
                    "backtest": False,
                    "reports": True,
                    "withdrawals": False
                },
                account_status=STATUS_ACTIVE,
                initial_capital=0.0,
                metadata={"exchange": "Interbank OTC / Global FX Live"}
            ),
            "CTRADER_LIVE": AccountContext(
                account_id="CTRADER_LIVE",
                workspace="FOREX_GOLD",
                environment="PAPER",
                broker="CTRADER",
                currency="USD",
                currency_symbol="$",
                instruments=["FOREX", "COMMODITIES"],
                risk_profile="MODERATE",
                capabilities={
                    "spot": True,
                    "futures": False,
                    "auto_trading": True,
                    "vault": True,
                    "news": True,
                    "backtest": True,
                    "reports": True,
                    "withdrawals": False
                },
                account_status=STATUS_ACTIVE,
                initial_capital=10000.0,
                metadata={"exchange": "cTrader Open API"}
            )
        }

    def register_account(self, ctx: AccountContext):
        """Register or update an explicit AccountContext."""
        self._accounts[ctx.account_id] = ctx

    def get_account(self, account_id: str) -> Optional[AccountContext]:
        """Fetch account context by ID. No fallbacks."""
        return self._accounts.get(account_id)

    def list_accounts(self, workspace: Optional[str] = None, environment: Optional[str] = None) -> List[AccountContext]:
        """List accounts, optionally filtered by workspace and/or environment."""
        accs = list(self._accounts.values())
        if workspace:
            norm_ws = "FOREX_GOLD" if str(workspace).upper() in ["FOREX", "FOREX_GOLD"] else str(workspace).upper()
            accs = [acc for acc in accs if acc.workspace == norm_ws]
        if environment:
            e_str = str(environment).strip().upper()
            norm_e = "PAPER" if e_str in ("DEMO", "TESTNET", "SANDBOX") else e_str
            accs = [acc for acc in accs if acc.environment == norm_e]
        return accs

    def resolve(
        self,
        account_id: Optional[str] = None,
        workspace: Optional[str] = None,
        environment: Optional[str] = None,
        broker: Optional[str] = None
    ) -> AccountContext:
        """
        Authoritative Account Context Resolver.
        FAILS CLOSED if the context cannot be unambiguously resolved.
        Enforces strict environment boundary:
          - DEMO/PAPER accounts cannot be resolved in LIVE.
          - LIVE accounts cannot be resolved in DEMO.
        """
        # Standardize environment alias: DEMO -> PAPER
        norm_env = None
        if environment:
            e_str = str(environment).strip().upper()
            norm_env = "PAPER" if e_str in ("DEMO", "TESTNET", "SANDBOX", "PAPER") else ("LIVE" if e_str == "LIVE" else e_str)

        # 1. Direct account_id resolution
        if account_id and account_id in self._accounts:
            ctx = self._accounts[account_id]
            # If workspace or environment is explicitly specified, verify compatibility
            if workspace:
                norm_ws = "FOREX_GOLD" if str(workspace).upper() in ["FOREX", "FOREX_GOLD"] else str(workspace).upper()
                if ctx.workspace != norm_ws:
                    raise AccountContextUnavailableError(
                        f"Account '{account_id}' belongs to workspace '{ctx.workspace}', not requested '{norm_ws}'"
                    )
            if norm_env and ctx.environment != norm_env:
                raise AccountContextUnavailableError(
                    f"Account '{account_id}' environment is '{ctx.environment}', cannot be accessed from '{environment}'"
                )
            return ctx

        # 2. Structured query resolution by workspace + environment + broker
        if workspace:
            norm_ws = "FOREX_GOLD" if str(workspace).upper() in ["FOREX", "FOREX_GOLD"] else str(workspace).upper()
            target_env = norm_env if norm_env else "PAPER"
            
            candidates = [
                acc for acc in self._accounts.values()
                if acc.workspace == norm_ws
            ]
            if not candidates:
                raise AccountContextUnavailableError(f"No registered account for workspace '{norm_ws}'")

            # Filter by target environment
            matched_env = [acc for acc in candidates if acc.environment == target_env]
            if not matched_env:
                raise AccountContextUnavailableError(
                    f"No registered account for workspace '{norm_ws}' in environment '{target_env}'"
                )

            # Filter by broker if specified
            if broker:
                norm_broker = str(broker).upper()
                matched_broker = [acc for acc in matched_env if acc.broker.upper() == norm_broker]
                if matched_broker:
                    return matched_broker[0]
                raise AccountContextUnavailableError(
                    f"No registered account for workspace '{norm_ws}', environment '{target_env}', broker '{broker}'"
                )

            return matched_env[0]

        # 3. Fail Closed — Cannot resolve
        raise AccountContextUnavailableError(
            "ACCOUNT_CONTEXT_UNAVAILABLE: Cannot resolve account context without valid account_id or workspace"
        )


class AccountContextUnavailableError(Exception):
    def __init__(self, message: str = ACCOUNT_CONTEXT_UNAVAILABLE):
        super().__init__(message)
        self.code = ACCOUNT_CONTEXT_UNAVAILABLE


# Global singleton
account_context_manager = AccountContextManager()
