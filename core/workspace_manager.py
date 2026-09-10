"""
Aegis-Quant Authoritative Workspace Manager.
Enforces strict workspace / asset-class boundaries across:
  - INDIA (INR ₹) -> AEGIS_INDIA_INR (Upstox / NSE / BSE)
  - FOREX_GOLD (USD $) -> AEGIS_QUANT_MASTER (Interbank OTC / Global FX)
  - CRYPTO (USDT $) -> BINANCE_TESTNET_DEMO / BINANCE_LIVE_REAL (Binance)

Default workspace: INDIA
Persisted in: data/workspace_state.json
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
WORKSPACE_STATE_FILE = Path(__file__).resolve().parent.parent / 'data' / 'workspace_state.json'


class WorkspaceManager:
    WORKSPACE_INDIA = 'INDIA'
    WORKSPACE_FOREX_GOLD = 'FOREX_GOLD'
    WORKSPACE_CRYPTO = 'CRYPTO'

    VALID_WORKSPACES: Set[str] = {WORKSPACE_INDIA, WORKSPACE_FOREX_GOLD, WORKSPACE_CRYPTO}

    METADATA: Dict[str, Dict[str, Any]] = {
        WORKSPACE_INDIA: {
            'name': 'Indian Markets (NSE/BSE)',
            'workspace': WORKSPACE_INDIA,
            'currency': 'INR',
            'currency_symbol': '₹',
            'default_pool': 'AEGIS_INDIA_INR',
            'allowed_pools': ['AEGIS_INDIA_INR', 'UPSTOX_DEMO', 'UPSTOX_LIVE'],
            'venue_name': 'Upstox / NSE / BSE',
            'settlement': 'T+1 Rolling',
            'regulation': 'SEBI Compliant',
            'initial_capital': 100000.0,
            'max_leverage': 5.0,
            'instruments': [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
                'SBIN', 'BHARTIARTL', 'ITC', 'LICI', 'LT',
                'NIFTY50', 'BANKNIFTY', 'NIFTYBEES', 'GOLDBEES', 'BANKBEES', 'ITBEES'
            ],
            'asset_categories': ['INDIAN_STOCKS', 'INDIAN_EQUITY', 'INDIAN_ETF', 'INDIAN_INDEX'],
            'funding_methods': ['UPI', 'NetBanking', 'NEFT', 'RTGS'],
            'flag': '🇮🇳',
            'badge_text': 'UPSTOX: NSE/BSE ACTIVE'
        },
        WORKSPACE_FOREX_GOLD: {
            'name': 'Forex & Commodities (Global)',
            'workspace': WORKSPACE_FOREX_GOLD,
            'currency': 'USD',
            'currency_symbol': '$',
            'default_pool': 'AEGIS_QUANT_MASTER',
            'allowed_pools': ['AEGIS_QUANT_MASTER'],
            'venue_name': 'Interbank OTC / Global FX',
            'settlement': 'T+2 Rolling Spot',
            'regulation': 'Global Multi-Regulated OTC',
            'initial_capital': 100000.0,
            'max_leverage': 20.0,
            'instruments': [
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                'USDCHF', 'NZDUSD', 'XAUUSD', 'USDINR', 'EURINR'
            ],
            'asset_categories': ['FOREX', 'COMMODITIES'],
            'funding_methods': ['Bank Wire', 'ACH', 'Credit Card'],
            'flag': '💱',
            'badge_text': 'FOREX: 24/5 INTERBANK ACTIVE'
        },
        WORKSPACE_CRYPTO: {
            'name': 'Crypto Markets (Binance)',
            'workspace': WORKSPACE_CRYPTO,
            'currency': 'USDT',
            'currency_symbol': '$',
            'default_pool': 'BINANCE_TESTNET_DEMO',
            'allowed_pools': ['BINANCE_TESTNET_DEMO', 'BINANCE_LIVE_REAL', 'BINANCE_DEMO', 'BINANCE_LIVE'],
            'venue_name': 'Binance Spot & Futures',
            'settlement': 'Instant On-Chain / Off-Chain',
            'regulation': 'Binance Institutional VASP',
            'initial_capital': 19950.55,
            'max_leverage': 25.0,
            'instruments': [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
                'DOGEUSDT', 'ADAUSDT', 'BTCUSD', 'ETHUSD', 'SOLUSD'
            ],
            'asset_categories': ['CRYPTO'],
            'funding_methods': ['USDT (TRC20/ERC20)', 'Binance Pay'],
            'flag': '🌐',
            'badge_text': 'BINANCE: 24/7 SPOT ENGINE ACTIVE'
        }
    }

    def __init__(self):
        self._active_workspace: str = self.WORKSPACE_INDIA
        self._switch_count: int = 0
        self._load_state()

    def _normalize_workspace(self, ws: Optional[str]) -> str:
        if not ws:
            return self._active_workspace
        clean = str(ws).strip().upper().replace(' ', '_')
        if clean in ['INDIA', 'INDIA_INR', 'NSE', 'BSE', 'UPSTOX']:
            return self.WORKSPACE_INDIA
        if clean in ['FOREX', 'FOREX_GOLD', 'GOLD', 'COMMODITIES', 'FX', 'GLOBAL_FX']:
            return self.WORKSPACE_FOREX_GOLD
        if clean in ['CRYPTO', 'BINANCE', 'USDT', 'CRYPTO_USDT']:
            return self.WORKSPACE_CRYPTO
        return clean

    def _load_state(self):
        WORKSPACE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if WORKSPACE_STATE_FILE.exists():
            try:
                with open(WORKSPACE_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    ws = self._normalize_workspace(data.get('active_workspace'))
                    if ws in self.VALID_WORKSPACES:
                        self._active_workspace = ws
                        self._switch_count = int(data.get('switch_count', 0))
                        return
            except Exception as e:
                print(f'[WORKSPACE_MGR] Load state error: {e}')
        self._active_workspace = self.WORKSPACE_INDIA
        self._save_state()

    def _save_state(self):
        try:
            WORKSPACE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = WORKSPACE_STATE_FILE.with_suffix('.tmp')
            now_str = datetime.now(timezone.utc).astimezone(IST_TZ).strftime('%Y-%m-%d %H:%M:%S IST')
            data = {
                'active_workspace': self._active_workspace,
                'switch_count': self._switch_count,
                'updated_at': now_str,
                'metadata': self.METADATA.get(self._active_workspace, {})
            }
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=2)
            tmp.replace(WORKSPACE_STATE_FILE)
        except Exception as e:
            print(f'[WORKSPACE_MGR] Save state error: {e}')

    def get_active_workspace(self) -> str:
        return self._active_workspace

    def get_workspace_meta(self, workspace: Optional[str] = None) -> Dict[str, Any]:
        ws = self._normalize_workspace(workspace)
        return self.METADATA.get(ws, self.METADATA[self.WORKSPACE_INDIA])

    def get_metadata(self, workspace: Optional[str] = None) -> Dict[str, Any]:
        return self.get_workspace_meta(workspace)

    def get_workspace_for_symbol(self, symbol: str) -> Optional[str]:
        if not symbol:
            return None
        sym = str(symbol).strip().upper()
        for ws, meta in self.METADATA.items():
            if sym in meta['instruments']:
                return ws
        if sym.endswith('.NS') or sym.endswith('.BO') or 'NIFTY' in sym or 'BEES' in sym:
            return self.WORKSPACE_INDIA
        if sym.endswith('USDT') or sym.endswith('BUSD') or (sym.startswith('BTC') and 'INR' not in sym) or (sym.startswith('ETH') and 'INR' not in sym):
            return self.WORKSPACE_CRYPTO
        if any(c in sym for c in ['EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 'XAU']):
            return self.WORKSPACE_FOREX_GOLD
        return None

    def is_symbol_allowed(self, symbol: str, workspace: Optional[str] = None) -> bool:
        ws = self._normalize_workspace(workspace)
        expected_ws = self.get_workspace_for_symbol(symbol)
        if expected_ws is None:
            return symbol.strip().upper() in self.METADATA.get(ws, {}).get('instruments', [])
        return expected_ws == ws

    def validate_order_workspace(self, symbol: str, workspace: Optional[str] = None) -> Tuple[bool, str]:
        ws = self._normalize_workspace(workspace)
        sym = str(symbol).strip().upper()
        if not self.is_symbol_allowed(sym, ws):
            return (
                False,
                f'WORKSPACE_ASSET_MISMATCH: Instrument {sym} does not belong to {ws} workspace'
            )
        return (True, 'WORKSPACE_OK')

    def set_active_workspace(self, workspace: str) -> Dict[str, Any]:
        target_ws = self._normalize_workspace(workspace)
        if target_ws not in self.VALID_WORKSPACES:
            raise ValueError(f'Invalid workspace {workspace}. Valid: {list(self.VALID_WORKSPACES)}')

        prev_ws = self._active_workspace
        self._active_workspace = target_ws
        self._switch_count += 1
        self._save_state()

        meta = self.METADATA[target_ws]
        target_pool = meta['default_pool']

        try:
            from execution.paper_broker import paper_broker
            paper_broker.set_active_capital_pool(target_pool, initial_capital=meta['initial_capital'])
        except Exception as e:
            print(f'[WORKSPACE_MGR] Pool sync notice: {e}')

        try:
            from core.double_entry_ledger import double_entry_ledger
            double_entry_ledger.ensure_opening_balance(
                environment=target_pool,
                amount=meta['initial_capital'],
                asset=meta['currency']
            )
        except Exception as e:
            print(f'[WORKSPACE_MGR] Ledger opening balance notice: {e}')

        try:
            from core.audit_logger import audit_logger
            audit_logger.log_event(
                event_type='WORKSPACE_SWITCH',
                user_id='OPERATOR',
                amount=0.0,
                asset=meta['currency'],
                reference_id=f'SWITCH_{prev_ws}_TO_{target_ws}',
                environment=target_pool
            )
        except Exception as e:
            print(f'[WORKSPACE_MGR] Audit log notice: {e}')

        return {
            'status': 'SUCCESS',
            'previous_workspace': prev_ws,
            'active_workspace': target_ws,
            'active_pool': target_pool,
            'currency': meta['currency'],
            'currency_symbol': meta['currency_symbol'],
            'initial_capital': meta['initial_capital'],
            'venue_name': meta['venue_name'],
            'instruments': meta['instruments'],
            'switch_count': self._switch_count
        }

workspace_manager = WorkspaceManager()
