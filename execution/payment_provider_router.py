"""
Aegis-Quant Payment Provider Router.
Abstract factory over all payment providers.
Currently supported: Binance Pay, Stripe.
Routes to the appropriate provider based on explicit selection.
Stripe remains in the architecture even when inactive.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class PaymentProviderRouter:
    """
    Abstract factory over payment providers.
    add_provider() registers new providers.
    create_deposit() routes to the selected provider.
    """

    PROVIDER_BINANCE_PAY = "BINANCE_PAY"
    PROVIDER_STRIPE      = "STRIPE"

    def __init__(self):
        # Providers imported lazily to avoid circular deps at startup
        self._providers: Dict[str, Any] = {}
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            from execution.binance_pay_engine import binance_pay_engine
            self._providers[self.PROVIDER_BINANCE_PAY] = binance_pay_engine
        except Exception as e:
            print(f"[PAYMENT_ROUTER] Binance Pay load notice: {e}")
        try:
            from execution.stripe_payment_engine import stripe_payment_engine
            self._providers[self.PROVIDER_STRIPE] = stripe_payment_engine
        except Exception as e:
            print(f"[PAYMENT_ROUTER] Stripe load notice: {e}")
        self._initialized = True

    def get_provider_statuses(self) -> Dict[str, Any]:
        """Return health and config status for all providers."""
        self._ensure_initialized()
        statuses = {}

        # Binance Pay
        bp = self._providers.get(self.PROVIDER_BINANCE_PAY)
        if bp:
            statuses["BINANCE_PAY"] = bp.get_provider_status()
        else:
            statuses["BINANCE_PAY"] = {"status": "NOT_LOADED", "enabled": False}

        # Stripe
        sp = self._providers.get(self.PROVIDER_STRIPE)
        if sp:
            statuses["STRIPE"] = {
                "provider":    "STRIPE",
                "enabled":     True,
                "environment": getattr(sp, "mode", "TEST"),
                "configured":  bool(getattr(sp, "secret_key", "") and not getattr(sp, "secret_key", "").startswith("sk_test_51Mock")),
                "status":      "CONFIGURED" if (bool(getattr(sp, "secret_key", "")) and not getattr(sp, "secret_key", "").startswith("sk_test_51Mock")) else "TEST_MODE",
                "total_payments": len(getattr(sp, "payments", [])),
            }
        else:
            statuses["STRIPE"] = {"status": "NOT_LOADED", "enabled": False}

        return statuses

    def create_deposit(
        self,
        provider: str,
        amount: float,
        currency: str = "USDT",
        user_id: str = "USER-MAIN",
        **kwargs,
    ) -> Dict[str, Any]:
        """Route deposit creation to the selected provider."""
        self._ensure_initialized()

        if provider not in self._providers:
            return {
                "status":  "PROVIDER_NOT_FOUND",
                "message": f"Provider '{provider}' is not registered. Supported: {list(self._providers.keys())}",
            }

        engine = self._providers[provider]

        if provider == self.PROVIDER_BINANCE_PAY:
            return engine.create_payment_order(
                amount=amount, currency=currency, user_id=user_id,
                description=kwargs.get("description", "Aegis-Quant Deposit")
            )
        elif provider == self.PROVIDER_STRIPE:
            return engine.create_checkout_session(
                amount=amount, currency=kwargs.get("stripe_currency", "usd"), user_id=user_id
            )
        else:
            return {"status": "UNSUPPORTED_PROVIDER", "provider": provider}

    def verify_webhook(
        self,
        provider: str,
        payload: bytes,
        signature: str,
        **kwargs,
    ) -> bool:
        """Route webhook verification to the appropriate provider."""
        self._ensure_initialized()
        engine = self._providers.get(provider)
        if not engine:
            return False
        if provider == self.PROVIDER_BINANCE_PAY:
            timestamp = kwargs.get("timestamp", "")
            nonce     = kwargs.get("nonce", "")
            return engine.verify_webhook_signature(
                timestamp, nonce, payload.decode("utf-8"), signature
            )
        elif provider == self.PROVIDER_STRIPE:
            return engine.verify_webhook_signature(payload, signature)
        return False

    def process_webhook_event(
        self,
        provider: str,
        event_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route webhook event processing to the appropriate provider."""
        self._ensure_initialized()
        engine = self._providers.get(provider)
        if not engine:
            return {"status": "PROVIDER_NOT_FOUND"}
        return engine.process_webhook_event(event_data)


# Global singleton
payment_provider_router = PaymentProviderRouter()
