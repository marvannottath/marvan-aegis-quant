"""
Stripe Payment Gateway Engine — Webhook Signature Verification & Internal Mapping.
HMAC-SHA256 signature verification for stripe-signature header.
Maps payment checkout sessions to internal deposit IDs.
"""

import hmac
import hashlib
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional

class StripePaymentEngine:
    def __init__(self):
        self.mapped_sessions: Dict[str, Dict[str, Any]] = {}

    def verify_webhook_signature(self, payload_bytes: bytes, sig_header: str, secret: str) -> bool:
        """Verify official Stripe HMAC-SHA256 webhook signature header."""
        if not sig_header or not secret:
            return False
        try:
            pairs = dict(item.split("=") for item in sig_header.split(","))
            t = pairs.get("t")
            v1 = pairs.get("v1")
            if not t or not v1:
                return False

            signed_payload = f"{t}.".encode("utf-8") + payload_bytes
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_sig, v1)
        except Exception:
            return False

    def create_internal_session_mapping(self, deposit_id: str, user_id: str, amount_usd: float, currency: str = "usd") -> Dict[str, Any]:
        session_id = f"cs_stripe_{int(time.time()*1000)}"
        mapping = {
            "session_id": session_id,
            "deposit_id": deposit_id,
            "user_id": user_id,
            "amount_usd": round(amount_usd, 2),
            "currency": currency.lower(),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "AWAITING_PAYMENT"
        }
        self.mapped_sessions[session_id] = mapping
        return mapping


# Global Singleton
stripe_payment_engine = StripePaymentEngine()
