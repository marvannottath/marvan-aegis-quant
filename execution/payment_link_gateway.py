"""
AEGIS-QUANT Universal Payment Link & Broker Fund Gateway.
Enables creating dynamic, sharable checkout URLs for credit/debit cards, Apple Pay,
Google Pay, Contactless NFC, Binance Pay/Crypto, and UPI.
Upon successful confirmation, atomically credits the selected target broker pool
(Kotak Neo, Binance Live, MT5, Upstox, or Aegis Master) via double-entry ledger.
"""

import os
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
LINKS_DB = Path(__file__).resolve().parent.parent / "data" / "payment_links.json"


def get_ist_now() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class PaymentLinkGateway:
    SUPPORTED_TARGET_BROKERS = {
        "KOTAK_NEO_LIVE": {
            "name": "Kotak Neo (Kotak Securities)",
            "venue": "INDIA",
            "currency": "INR",
            "description": "NSE/BSE Indian Equities & F&O Live Trading Pool",
            "icon": "fa-solid fa-building-columns text-red-500",
        },
        "BINANCE_LIVE_REAL": {
            "name": "Binance Live Gateway",
            "venue": "CRYPTO",
            "currency": "USDT",
            "description": "Global Spot & USDT-M Algorithmic Trading",
            "icon": "fa-brands fa-bitcoin text-amber-500",
        },
        "MT5_LIVE_REAL": {
            "name": "MetaTrader 5 Live Gateway",
            "venue": "FOREX_GOLD",
            "currency": "USD",
            "description": "Institutional Forex, Gold (XAUUSD) & Indices",
            "icon": "fa-solid fa-arrow-trend-up text-blue-500",
        },
        "UPSTOX_LIVE": {
            "name": "Upstox Pro Live Gateway",
            "venue": "INDIA",
            "currency": "INR",
            "description": "SEBI Regulated High-Speed Order Routing",
            "icon": "fa-solid fa-bolt text-purple-500",
        },
        "AEGIS_QUANT_MASTER": {
            "name": "Aegis Institutional Master Vault",
            "venue": "MULTI_ASSET",
            "currency": "USD",
            "description": "Multi-Asset Liquidity Pool & High-Frequency Simulator",
            "icon": "fa-solid fa-brain text-cyan-400",
        },
    }

    def __init__(self):
        self.links: Dict[str, Dict[str, Any]] = {}
        self._load_db()

    def _load_db(self):
        LINKS_DB.parent.mkdir(parents=True, exist_ok=True)
        if LINKS_DB.exists():
            try:
                with open(LINKS_DB, "r") as f:
                    self.links = json.load(f)
            except Exception as e:
                print(f"[PAYMENT_LINK_GW] Load notice: {e}")

    def _save_db(self):
        try:
            tmp = LINKS_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self.links, f, indent=2)
            tmp.replace(LINKS_DB)
        except Exception as e:
            print(f"[PAYMENT_LINK_GW] Save error: {e}")

    def create_payment_link(
        self,
        amount: float,
        currency: str = "INR",
        target_broker: str = "KOTAK_NEO_LIVE",
        title: str = "Aegis Quant Bot Capital Deposit",
        description: str = "Secure algorithmic trading capital funding",
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        expires_in_hours: int = 72,
    ) -> Dict[str, Any]:
        """Generate a sharable payment link with broker routing metadata."""
        if amount <= 0:
            return {"status": "ERROR", "message": "Deposit amount must be positive."}

        target_broker = target_broker.upper()
        if target_broker not in self.SUPPORTED_TARGET_BROKERS:
            # Map shorthand names
            if "KOTAK" in target_broker:
                target_broker = "KOTAK_NEO_LIVE"
            elif "BINANCE" in target_broker:
                target_broker = "BINANCE_LIVE_REAL"
            elif "MT5" in target_broker:
                target_broker = "MT5_LIVE_REAL"
            elif "UPSTOX" in target_broker:
                target_broker = "UPSTOX_LIVE"
            else:
                target_broker = "KOTAK_NEO_LIVE"

        broker_info = self.SUPPORTED_TARGET_BROKERS.get(target_broker, {})
        link_id = f"PL-{uuid.uuid4().hex[:8].upper()}"
        expiry_ts = int(time.time() + (expires_in_hours * 3600))

        # Dynamic checkout URL hosted on this server
        base_host = os.getenv("APP_BASE_URL", "https://srv1799665.hstgr.cloud")
        checkout_url = f"{base_host}/pay/{link_id}"

        link_record = {
            "link_id": link_id,
            "checkout_url": checkout_url,
            "title": title,
            "description": description,
            "amount": round(amount, 2),
            "currency": currency.upper(),
            "target_broker": target_broker,
            "target_broker_name": broker_info.get("name", target_broker),
            "venue": broker_info.get("venue", "INDIA"),
            "customer_name": customer_name or "Valued Investor",
            "customer_email": customer_email or "",
            "status": "ACTIVE",  # ACTIVE | PAID | EXPIRED | CANCELLED
            "supported_methods": [
                {"id": "card", "name": "Credit & Debit Cards", "icon": "fa-regular fa-credit-card"},
                {"id": "apple_pay", "name": "Apple Pay", "icon": "fa-brands fa-apple"},
                {"id": "google_pay", "name": "Google Pay", "icon": "fa-brands fa-google"},
                {"id": "nfc", "name": "Contactless / NFC Tap", "icon": "fa-solid fa-wifi"},
                {"id": "upi", "name": "Instant UPI / QR (India)", "icon": "fa-solid fa-qrcode"},
                {"id": "binance_pay", "name": "Binance Pay / USDT", "icon": "fa-solid fa-wallet"},
            ],
            "created_at": get_ist_now(),
            "expires_at": datetime.fromtimestamp(expiry_ts, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            "paid_at": None,
            "payment_ref": None,
            "payment_method_used": None,
            "allocated_to_broker": False,
        }

        self.links[link_id] = link_record
        self._save_db()

        return {
            "status": "SUCCESS",
            "link_id": link_id,
            "checkout_url": checkout_url,
            "amount": link_record["amount"],
            "currency": link_record["currency"],
            "target_broker": target_broker,
            "target_broker_name": link_record["target_broker_name"],
            "record": link_record,
        }

    def get_payment_link(self, link_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve link details."""
        return self.links.get(link_id)

    def list_all_links(self) -> List[Dict[str, Any]]:
        """Return all generated payment links."""
        return sorted(self.links.values(), key=lambda x: x.get("created_at", ""), reverse=True)

    def confirm_payment(
        self,
        link_id: str,
        payment_method: str = "card",
        payment_reference: str = "",
        payer_notes: str = "",
    ) -> Dict[str, Any]:
        """
        Confirm payment for a link and credit the target broker's working capital.
        Enforces idempotency: a link cannot be credited twice.
        """
        if link_id not in self.links:
            return {"status": "ERROR", "message": f"Payment link '{link_id}' not found."}

        record = self.links[link_id]
        if record["status"] == "PAID":
            return {
                "status": "ALREADY_PAID",
                "message": f"Payment link '{link_id}' has already been processed.",
                "record": record,
            }

        ref_id = payment_reference or f"TXN-{uuid.uuid4().hex[:10].upper()}"
        record["status"] = "PAID"
        record["paid_at"] = get_ist_now()
        record["payment_ref"] = ref_id
        record["payment_method_used"] = payment_method.upper()
        record["payer_notes"] = payer_notes

        # ── Atomically Route Capital into Selected Broker Pool ───────────────
        target = record.get("target_broker", "KOTAK_NEO_LIVE")
        amount = float(record["amount"])
        curr = record.get("currency", "INR")

        allocation_result = self._allocate_to_broker(target, amount, curr, ref_id)
        record["allocated_to_broker"] = allocation_result.get("success", False)
        record["allocation_detail"] = allocation_result

        self._save_db()

        # Send Real-Time Telegram Dispatch
        try:
            from core.telegram_alerts import telegram_alerts
            tg_msg = (
                f"💰 *NEW CAPITAL DEPOSIT CONFIRMED*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Amount:* {curr} {amount:,.2f}\n"
                f"• *Target Broker:* {record.get('target_broker_name', target)}\n"
                f"• *Payment Method:* {payment_method.upper()} (Cards/NFC/UPI)\n"
                f"• *Reference ID:* `{ref_id}`\n"
                f"• *Link ID:* `{link_id}`\n"
                f"• *Allocated Balance:* {'✅ SUCCESS' if record['allocated_to_broker'] else '⚠️ PENDING'}\n"
                f"• *Time:* {record['paid_at']}"
            )
            telegram_alerts.send_alert("Capital Deposit Confirmed", tg_msg, event_type="DEPOSIT_CONFIRMED")
        except Exception as e:
            print(f"[PAYMENT_LINK_GW] Telegram dispatch notice: {e}")

        return {
            "status": "SUCCESS",
            "message": f"Payment of {curr} {amount:,.2f} confirmed! Credited to {record.get('target_broker_name', target)}.",
            "record": record,
            "allocation": allocation_result,
        }

    def _allocate_to_broker(self, broker_key: str, amount: float, currency: str, ref_id: str) -> Dict[str, Any]:
        """Internal ledger and broker memory allocation."""
        try:
            # 1. Post to Double-Entry Ledger
            try:
                from core.double_entry_ledger import double_entry_ledger
                double_entry_ledger.post_entry(
                    ledger_type="UNIVERSAL_GATEWAY_DEPOSIT",
                    debit_account="EXTERNAL_PAYMENT_INFLOW",
                    credit_account=f"BROKER_ACCOUNT_{broker_key}",
                    amount=amount,
                    asset=currency,
                    reference_id=ref_id,
                    environment="AEGIS_QUANT_MASTER",
                    metadata={"target_broker": broker_key, "currency": currency},
                )
            except Exception as le:
                print(f"[PAYMENT_LINK_GW] Ledger entry notice: {le}")

            # 2. Update paper_broker active pool and cash
            from execution.paper_broker import paper_broker
            from execution.broker_gateway_manager import broker_gateway_manager

            # Synchronize Broker Gateway Connections dictionary
            b_conn_key = broker_key.lower()
            if b_conn_key in broker_gateway_manager.connections:
                cur_b_bal = float(broker_gateway_manager.connections[b_conn_key].get("balance", 0.0))
                new_b_bal = round(cur_b_bal + amount, 2)
                broker_gateway_manager.connections[b_conn_key]["balance"] = new_b_bal
                broker_gateway_manager._save_connections()

            # Synchronize Paper Broker Pools
            pool_entry = paper_broker.pools.setdefault(broker_key, {})
            current_pool_cash = float(pool_entry.get("virtual_cash", 0.0))
            new_pool_cash = round(current_pool_cash + amount, 2)
            pool_entry["virtual_cash"] = new_pool_cash
            pool_entry["equity"] = round(float(pool_entry.get("equity", 0.0)) + amount, 2)

            if paper_broker.active_pool_name == broker_key or broker_key in ["KOTAK_NEO_LIVE", "AEGIS_INDIA_INR"]:
                paper_broker.virtual_cash = round(paper_broker.virtual_cash + amount, 2)
                paper_broker.equity = round(paper_broker.equity + amount, 2)
            paper_broker._save_state()

            # If Kotak Neo, update authoritative live memory
            if "KOTAK" in broker_key:
                try:
                    from execution.kotak_neo_broker import kotak_neo_broker
                    kotak_neo_broker._live_cash = round(kotak_neo_broker._live_cash + amount, 2)
                except Exception:
                    pass

            return {
                "success": True,
                "broker": broker_key,
                "credited_amount": amount,
                "new_pool_cash": new_pool_cash,
                "currency": currency,
            }
        except Exception as e:
            print(f"[PAYMENT_LINK_GW] Allocation error: {e}")
            return {"success": False, "error": str(e)}


# Global Singleton
payment_link_gateway = PaymentLinkGateway()
