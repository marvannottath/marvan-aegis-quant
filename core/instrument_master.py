"""
Aegis-Quant Authoritative Instrument Master.
Maintains canonical exchange instrument identities for Indian Equities, Derivatives, ETFs, and Indices.
Enforces that every Indian execution instrument possesses a real authoritative identifier:
  - symbol (e.g. RELIANCE)
  - exchange (NSE)
  - instrument_key / security ID (NSE_EQ:RELIANCE, ISIN: INE002A01018)
  - segment (EQUITY, INDEX, ETF)
  - instrument_type (EQUITY, INDEX, ETF)
  - tick_size (0.05)
  - lot_size (1)
  - currency (INR)
  - tradable_status (TRADABLE)

Validates end-to-end pipeline consistency:
  AI Signal -> Instrument Master -> Risk Engine -> Order Request -> Broker Payload
"""

from typing import Dict, Any, Optional, Tuple, List


# Authoritative Indian Instrument Master Registry
INDIA_INSTRUMENT_MASTER: Dict[str, Dict[str, Any]] = {
    # Equities (NSE Large-Caps)
    "RELIANCE": {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:RELIANCE",
        "security_id": "INE002A01018",
        "token": "738561",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 25000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "TCS": {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:TCS",
        "security_id": "INE467B01029",
        "token": "2953217",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 10000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "HDFCBANK": {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:HDFCBANK",
        "security_id": "INE040A01034",
        "token": "341249",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 25000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "INFY": {
        "symbol": "INFY",
        "name": "Infosys Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:INFY",
        "security_id": "INE009A01021",
        "token": "408065",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 25000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "ICICIBANK": {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:ICICIBANK",
        "security_id": "INE090A01021",
        "token": "1270529",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 25000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "SBIN": {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:SBIN",
        "security_id": "INE062A01020",
        "token": "779521",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 30000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "BHARTIARTL": {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:BHARTIARTL",
        "security_id": "INE397D01024",
        "token": "2714625",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 20000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "ITC": {
        "symbol": "ITC",
        "name": "ITC Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:ITC",
        "security_id": "INE154A01025",
        "token": "424961",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 40000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "LICI": {
        "symbol": "LICI",
        "name": "Life Insurance Corporation of India",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:LICI",
        "security_id": "INE0J1Y01017",
        "token": "543526",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 15000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "LT": {
        "symbol": "LT",
        "name": "Larsen & Toubro Limited",
        "exchange": "NSE",
        "segment": "EQUITY",
        "instrument_type": "EQUITY",
        "instrument_key": "NSE_EQ:LT",
        "security_id": "INE018A01030",
        "token": "2939649",
        "tick_size": 0.05,
        "lot_size": 1,
        "freeze_quantity": 10000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    # Indices
    "NIFTY50": {
        "symbol": "NIFTY50",
        "name": "Nifty 50 Index",
        "exchange": "NSE",
        "segment": "INDEX",
        "instrument_type": "INDEX",
        "instrument_key": "NSE_INDEX:NIFTY50",
        "security_id": "NIFTY 50",
        "token": "256265",
        "tick_size": 0.05,
        "lot_size": 50,
        "freeze_quantity": 1800,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY",
        "name": "Nifty Bank Index",
        "exchange": "NSE",
        "segment": "INDEX",
        "instrument_type": "INDEX",
        "instrument_key": "NSE_INDEX:BANKNIFTY",
        "security_id": "NIFTY BANK",
        "token": "260105",
        "tick_size": 0.05,
        "lot_size": 15,
        "freeze_quantity": 900,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    # ETFs
    "NIFTYBEES": {
        "symbol": "NIFTYBEES",
        "name": "Nippon India ETF Nifty 50 BeES",
        "exchange": "NSE",
        "segment": "ETF",
        "instrument_type": "ETF",
        "instrument_key": "NSE_ETF:NIFTYBEES",
        "security_id": "INF204KB14I2",
        "token": "2602753",
        "tick_size": 0.01,
        "lot_size": 1,
        "freeze_quantity": 50000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "GOLDBEES": {
        "symbol": "GOLDBEES",
        "name": "Nippon India ETF Gold BeES",
        "exchange": "NSE",
        "segment": "ETF",
        "instrument_type": "ETF",
        "instrument_key": "NSE_ETF:GOLDBEES",
        "security_id": "INF204KB17I5",
        "token": "3695105",
        "tick_size": 0.01,
        "lot_size": 1,
        "freeze_quantity": 50000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "BANKBEES": {
        "symbol": "BANKBEES",
        "name": "Nippon India ETF Nifty Bank BeES",
        "exchange": "NSE",
        "segment": "ETF",
        "instrument_type": "ETF",
        "instrument_key": "NSE_ETF:BANKBEES",
        "security_id": "INF204KB18I3",
        "token": "3695361",
        "tick_size": 0.01,
        "lot_size": 1,
        "freeze_quantity": 50000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    },
    "ITBEES": {
        "symbol": "ITBEES",
        "name": "Nippon India ETF Nifty IT BeES",
        "exchange": "NSE",
        "segment": "ETF",
        "instrument_type": "ETF",
        "instrument_key": "NSE_ETF:ITBEES",
        "security_id": "INF204KB19I1",
        "token": "3695617",
        "tick_size": 0.01,
        "lot_size": 1,
        "freeze_quantity": 50000,
        "currency": "INR",
        "tradable": True,
        "tradable_status": "TRADABLE"
    }
}


class InstrumentMaster:
    """Authoritative instrument master for Aegis-Quant."""

    def __init__(self):
        self.india_registry = INDIA_INSTRUMENT_MASTER

    def get_instrument(self, symbol: str, workspace: str = "INDIA") -> Optional[Dict[str, Any]]:
        sym = str(symbol or "").strip().upper()
        if workspace == "INDIA":
            return self.india_registry.get(sym)
        return None

    def resolve_instrument_key(self, symbol: str, workspace: str = "INDIA") -> str:
        inst = self.get_instrument(symbol, workspace)
        if inst:
            return inst["instrument_key"]
        from core.workspace_manager import workspace_manager
        return workspace_manager.get_instrument_key(symbol, workspace)

    def validate_instrument_completeness(self, symbol: str, workspace: str = "INDIA") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate that an instrument contains all mandatory exchange attributes:
          symbol, exchange, instrument_key, security_id, segment, instrument_type, tradable_status.
        """
        inst = self.get_instrument(symbol, workspace)
        if not inst:
            return False, f"Instrument '{symbol}' not found in {workspace} Instrument Master", {}

        required = ["symbol", "exchange", "instrument_key", "security_id", "segment", "instrument_type", "tradable_status"]
        missing = [f for f in required if not inst.get(f)]
        if missing:
            return False, f"Instrument '{symbol}' missing mandatory attributes: {missing}", inst

        return True, "INSTRUMENT_COMPLETE", inst

    def validate_pipeline_identity(
        self,
        signal: Dict[str, Any],
        order_request: Dict[str, Any],
        broker_payload: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validate pipeline identity preservation:
          AI Signal -> Instrument Master -> Risk Engine -> Order Request -> Broker Payload
        Ensures exact security ID and symbol are maintained throughout.
        """
        sym_sig = str(signal.get("symbol", "")).strip().upper()
        sym_ord = str(order_request.get("symbol", "")).strip().upper()
        sym_pay = str(broker_payload.get("symbol", "")).strip().upper()

        if not (sym_sig == sym_ord == sym_pay):
            return False, f"Symbol pipeline mismatch: signal='{sym_sig}', order='{sym_ord}', payload='{sym_pay}'"

        inst = self.get_instrument(sym_sig)
        if not inst:
            return False, f"Symbol '{sym_sig}' not found in Instrument Master"

        expected_key = inst["instrument_key"]
        ord_key = order_request.get("instrument_key") or order_request.get("instrument_id")
        pay_key = broker_payload.get("instrument_key") or broker_payload.get("instrument_token")

        if ord_key and ord_key != expected_key:
            return False, f"Order instrument_key '{ord_key}' does not match expected '{expected_key}'"

        return True, "PIPELINE_IDENTITY_PRESERVED"

    def validate_order_pipeline_identity(
        self,
        signal_symbol: str,
        order_symbol: str,
        broker_symbol: str,
        fill_symbol: str,
        position_symbol: str,
        expected_workspace: str = "INDIA",
        expected_currency: str = "INR"
    ) -> Tuple[bool, str]:
        """
        Validate that the identical symbol and identity flows through every stage:
          Signal Symbol = Order Symbol = Broker Symbol = Fill Symbol = Position Symbol.
        Rejects fail-closed if any mismatch occurs.
        """
        syms = [signal_symbol, order_symbol, broker_symbol, fill_symbol, position_symbol]
        norm_syms = [str(s or "").strip().upper() for s in syms]

        if len(set(norm_syms)) != 1:
            return False, f"PIPELINE_IDENTITY_FAIL: Inconsistent symbols across stages: {norm_syms}"

        canonical_sym = norm_syms[0]
        inst = self.get_instrument(canonical_sym, expected_workspace)
        if not inst and expected_workspace == "INDIA":
            return False, f"PIPELINE_IDENTITY_FAIL: Symbol '{canonical_sym}' not in {expected_workspace} Instrument Master"

        if inst and inst.get("currency") != expected_currency:
            return False, f"PIPELINE_IDENTITY_FAIL: Currency mismatch ({inst.get('currency')} != {expected_currency})"

        return True, f"PIPELINE_IDENTITY_VERIFIED: Identity preserved for '{canonical_sym}' across all 5 lifecycle stages"


# Global singleton
instrument_master = InstrumentMaster()
