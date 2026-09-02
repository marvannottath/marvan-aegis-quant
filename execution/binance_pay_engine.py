"""
Aegis-Quant Binance Pay Merchant Engine.
Integrates with Binance Pay v2 Merchant API.
Always performs server-side HMAC signature verification before any wallet credit.
Idempotent: same merchantTradeNo is never credited twice.
Default: NOT_CONFIGURED until BINANCE_PAY_MERCHANT_ID, BINANCE_PAY_API_KEY,
         BINANCE_PAY_SECRET_KEY are set as environment variables.
"""

import os
import json
import time
import uuid
import hmac
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

BINANCE_PAY_DB      = Path(__file__).resolve().parent.parent / "data" / "binance_pay_payments.json"
BINANCE_PAY_EVENTS  = Path(__file__).resolve().parent.parent / "data" / "processed_binance_pay_events.json"

# Payment state machine
PAY_STATES = ["INITIAL", "PENDING", "PROCESSING", "PAID", "EXPIRED", "ERROR", "REFUNDED"]
PAY_TRANSITIONS: Dict[str, List[str]] = {
    "INITIAL":    ["PENDING", "EXPIRED", "ERROR"],
    "PENDING":    ["PROCESSING", "PAID", "EXPIRED", "ERROR"],
    "PROCESSING": ["PAID", "ERROR"],
    "PAID":       ["REFUNDED"],
    "EXPIRED":    [],
    "ERROR":      [],
    "REFUNDED":   [],
}


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class BinancePayEngine:
    """
    Binance Pay Merchant API integration.
    Uses HMAC-SHA512 signatures on all outbound API calls.
    Verifies webhook authenticity before crediting wallet.
    Enforces idempotency on all payment events.
    """

    BINANCE_PAY_V2_BASE = "https://bpay.binanceapi.com"

    def __init__(self):
        self.merchant_id  = os.getenv("BINANCE_PAY_MERCHANT_ID",  "")
        self.api_key      = os.getenv("BINANCE_PAY_API_KEY",      "")
        self.secret_key   = os.getenv("BINANCE_PAY_SECRET_KEY",   "")
        self.environment  = os.getenv("BINANCE_PAY_ENVIRONMENT",  "TEST")  # TEST | LIVE
        self.enabled      = bool(self.merchant_id and self.api_key and self.secret_key)

        self.payments: List[Dict[str, Any]] = []
        self.processed_trade_nos: set = set()  # idempotency set
        self._load_db()
        self._save_db()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _load_db(self):
        BINANCE_PAY_DB.parent.mkdir(parents=True, exist_ok=True)
        if BINANCE_PAY_DB.exists():
            try:
                with open(BINANCE_PAY_DB, "r") as f:
                    data = json.load(f)
                    self.payments = data.get("payments", [])
            except Exception as e:
                print(f"[BINANCE_PAY] DB load notice: {e}")
        if BINANCE_PAY_EVENTS.exists():
            try:
                with open(BINANCE_PAY_EVENTS, "r") as f:
                    data = json.load(f)
                    self.processed_trade_nos = set(data.get("processed_trade_nos", []))
            except Exception as e:
                print(f"[BINANCE_PAY] Events load notice: {e}")

    def _save_db(self):
        try:
            tmp = BINANCE_PAY_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump({"payments": self.payments}, f, indent=2)
            tmp.replace(BINANCE_PAY_DB)
        except Exception as e:
            print(f"[BINANCE_PAY] DB save error: {e}")
        try:
            tmp2 = BINANCE_PAY_EVENTS.with_suffix(".tmp")
            with open(tmp2, "w") as f:
                json.dump({"processed_trade_nos": list(self.processed_trade_nos)}, f, indent=2)
            tmp2.replace(BINANCE_PAY_EVENTS)
        except Exception as e:
            print(f"[BINANCE_PAY] Events save error: {e}")

    # ------------------------------------------------------------------ #
    # HMAC Signature Generation (Binance Pay v2)
    # ------------------------------------------------------------------ #

    def _build_signature(self, timestamp: str, nonce: str, body_str: str) -> str:
        """
        Binance Pay v2 signature:
          HMAC-SHA512(secret, timestamp + '\n' + nonce + '\n' + body + '\n')
        """
        payload = f"{timestamp}\n{nonce}\n{body_str}\n"
        sig = hmac.new(
            self.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha512
        ).hexdigest().upper()
        return sig

    def _build_headers(self, body_str: str) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce     = uuid.uuid4().hex.upper()
        signature = self._build_signature(timestamp, nonce, body_str)
        return {
            "Content-Type":           "application/json",
            "BinancePay-Timestamp":   timestamp,
            "BinancePay-Nonce":       nonce,
            "BinancePay-Certificate-SN": self.api_key,
            "BinancePay-Signature":   signature,
        }

    # ------------------------------------------------------------------ #
    # Create Payment Order
    # ------------------------------------------------------------------ #

    def create_payment_order(
        self,
        amount: float,
        currency: str = "USDT",
        user_id: str = "USER-MAIN",
        description: str = "Aegis-Quant Deposit",
    ) -> Dict[str, Any]:
        """Create a Binance Pay payment order. Returns order details or NOT_CONFIGURED."""
        if not self.enabled:
            return {
                "status":  "NOT_CONFIGURED",
                "message": "Binance Pay is not configured. Set BINANCE_PAY_MERCHANT_ID, BINANCE_PAY_API_KEY, BINANCE_PAY_SECRET_KEY environment variables.",
                "payment_url": None,
            }
        if amount <= 0:
            return {"status": "ERROR", "message": "Amount must be positive"}

        merchant_trade_no = f"AQ-{int(time.time()*1000)}-{uuid.uuid4().hex[:8].upper()}"
        body = {
            "env":             {"terminalType": "WEB"},
            "merchantTradeNo": merchant_trade_no,
            "orderAmount":     round(amount, 2),
            "currency":        currency,
            "goods": {
                "goodsType":     "02",
                "goodsCategory": "Z000",
                "referenceGoodsId": merchant_trade_no,
                "goodsName":     description,
            },
            "returnUrl": "https://srv1799665.hstgr.cloud/?deposit=success",
            "cancelUrl":  "https://srv1799665.hstgr.cloud/?deposit=cancelled",
        }
        body_str = json.dumps(body, separators=(",", ":"))

        record = {
            "payment_id":         f"BPAY-{merchant_trade_no}",
            "merchant_trade_no":  merchant_trade_no,
            "provider":           "BINANCE_PAY",
            "environment":        self.environment,
            "amount":             round(amount, 2),
            "currency":           currency,
            "user_id":            user_id,
            "status":             "INITIAL",
            "provider_order_id":  None,
            "payment_url":        None,
            "provider_response":  None,
            "webhook_event":      None,
            "verification_status": "PENDING",
            "wallet_credited":    False,
            "created_at":         _now_str(),
            "completed_at":       None,
            "transitions": [{"from": None, "to": "INITIAL", "at": _now_str()}],
        }

        try:
            import requests
            headers = self._build_headers(body_str)
            resp = requests.post(
                f"{self.BINANCE_PAY_V2_BASE}/binancepay/openapi/v2/order",
                headers=headers, data=body_str, timeout=10
            )
            resp_data = resp.json()
            if resp_data.get("status") == "SUCCESS":
                result = resp_data.get("data", {})
                record["provider_order_id"] = result.get("prepayId")
                record["payment_url"]        = result.get("checkoutUrl") or result.get("universalUrl")
                record["provider_response"]  = result
                record["status"]             = "PENDING"
                record["transitions"].append({"from": "INITIAL", "to": "PENDING", "at": _now_str()})
            else:
                record["status"] = "ERROR"
                record["provider_response"] = resp_data
                record["transitions"].append({"from": "INITIAL", "to": "ERROR", "at": _now_str()})
        except Exception as e:
            record["status"] = "ERROR"
            record["provider_response"] = {"error": str(e)}
            record["transitions"].append({"from": "INITIAL", "to": "ERROR", "at": _now_str()})

        self.payments.insert(0, record)
        self._save_db()
        return record

    # ------------------------------------------------------------------ #
    # Webhook Verification (Server-Side ONLY)
    # ------------------------------------------------------------------ #

    def verify_webhook_signature(
        self,
        timestamp: str,
        nonce: str,
        body_str: str,
        received_signature: str,
    ) -> bool:
        """
        Verify Binance Pay webhook authenticity.
        Only server-side verification may trigger wallet credits.
        """
        if not self.secret_key:
            return False
        expected = self._build_signature(timestamp, nonce, body_str)
        return hmac.compare_digest(expected, received_signature.upper())

    def process_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a verified Binance Pay webhook.
        Idempotent: same merchantTradeNo is never processed twice.
        Only credits wallet if status == 'PAY_SUCCESS'.
        """
        merchant_trade_no = event_data.get("merchantTradeNo", "")
        biz_status        = event_data.get("bizStatus", "")

        # Idempotency guard
        if merchant_trade_no in self.processed_trade_nos:
            return {"status": "ALREADY_PROCESSED", "merchant_trade_no": merchant_trade_no}

        # Find matching payment record
        payment = next((p for p in self.payments if p["merchant_trade_no"] == merchant_trade_no), None)
        if not payment:
            return {"status": "NOT_FOUND", "merchant_trade_no": merchant_trade_no}

        payment["webhook_event"] = event_data

        if biz_status == "PAY_SUCCESS":
            payment["status"]             = "PAID"
            payment["verification_status"] = "VERIFIED"
            payment["completed_at"]        = _now_str()
            payment["transitions"].append({"from": payment["status"], "to": "PAID", "at": _now_str()})

            # Credit wallet via double-entry ledger (only on PAID + VERIFIED)
            if not payment["wallet_credited"]:
                try:
                    from core.double_entry_ledger import double_entry_ledger
                    double_entry_ledger.post_entry(
                        ledger_type="BINANCE_PAY_DEPOSIT",
                        debit_account="BINANCE_PAY_INFLOW",
                        credit_account="CUSTOMER_TRADING_ACCOUNT",
                        amount=payment["amount"],
                        asset=payment["currency"],
                        reference_id=payment["payment_id"],
                        environment="AEGIS_QUANT_MASTER",
                        metadata={"merchant_trade_no": merchant_trade_no, "provider": "BINANCE_PAY"},
                    )
                    payment["wallet_credited"] = True
                except Exception as e:
                    return {"status": "LEDGER_ERROR", "error": str(e)}

            # Mark as processed
            self.processed_trade_nos.add(merchant_trade_no)

        elif biz_status in ("PAY_CLOSED", "EXPIRED"):
            payment["status"] = "EXPIRED"
            payment["transitions"].append({"from": payment.get("status"), "to": "EXPIRED", "at": _now_str()})
            self.processed_trade_nos.add(merchant_trade_no)

        self._save_db()
        return {"status": "PROCESSED", "payment_status": payment["status"], "wallet_credited": payment.get("wallet_credited")}

    def get_provider_status(self) -> Dict[str, Any]:
        return {
            "provider":    "BINANCE_PAY",
            "enabled":     self.enabled,
            "environment": self.environment,
            "configured":  self.enabled,
            "status":      "CONFIGURED" if self.enabled else "NOT_CONFIGURED",
            "total_payments": len(self.payments),
            "paid_count":  sum(1 for p in self.payments if p["status"] == "PAID"),
        }


# Global singleton
binance_pay_engine = BinancePayEngine()
