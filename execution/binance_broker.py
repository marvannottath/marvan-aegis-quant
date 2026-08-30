"""
Official Binance API Broker Integration Engine.
Strict Institutional Connection & Authentication Verification.
Masks API Secrets and provides truthful connection status enums.
"""

import hmac
import hashlib
import time
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional

BINANCE_CONFIG_FILE = Path(__file__).resolve().parent / "binance_config.json"

class BinanceBroker:
    def __init__(self):
        self.api_key: str = ""
        self.secret_key: str = ""
        self.status: str = "DISCONNECTED"  # DISCONNECTED, UNAUTHENTICATED, AUTHENTICATED_READ_ONLY, LIVE_TRADING_ACTIVE, API_ERROR
        self.account_balance_usd: float = 0.0
        self.testnet: bool = False
        self.base_url: str = "https://api.binance.com"
        self._load_config()

    def _load_config(self):
        """Load saved Binance credentials and verify real exchange status."""
        if BINANCE_CONFIG_FILE.exists():
            try:
                with open(BINANCE_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.api_key = data.get("api_key", "").strip()
                    self.secret_key = data.get("secret_key", "").strip()
                    self.testnet = data.get("testnet", False)
                    self.base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"

                    if not self.api_key or not self.secret_key:
                        self.status = "UNAUTHENTICATED"
                    elif self.api_key in ["dummy", "test", "demo"]:
                        self.status = "SIMULATED_DEMO"
                    else:
                        # Test real connection
                        self.verify_connection()
            except Exception as e:
                print(f"[BINANCE] Load config notice: {e}")
                self.status = "CONFIG_ERROR"
        else:
            self.status = "UNAUTHENTICATED"

    def verify_connection(self) -> Dict[str, Any]:
        """Ping Binance /api/v3/account to verify genuine cryptographic signature."""
        if not self.api_key or not self.secret_key:
            self.status = "UNAUTHENTICATED"
            return {"status": self.status, "connected": False, "message": "API Key or Secret missing."}

        if self.api_key.lower() in ["dummy", "demo", "test"]:
            self.status = "SIMULATED_DEMO"
            return {"status": self.status, "connected": False, "message": "Demo mode active. Live Binance API key required for live execution."}

        try:
            ts = int(time.time() * 1000)
            query = f"timestamp={ts}"
            signature = hmac.new(
                self.secret_key.encode("utf-8"),
                query.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers = {"X-MBX-APIKEY": self.api_key}
            url = f"{self.base_url}/api/v3/account?{query}&signature={signature}"
            resp = requests.get(url, headers=headers, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                can_trade = data.get("canTrade", False)
                self.status = "LIVE_TRADING_ACTIVE" if can_trade else "AUTHENTICATED_READ_ONLY"
                
                # Sum USDT/BUSD balances
                balances = data.get("balances", [])
                usdt = sum(float(b["free"]) for b in balances if b["asset"] in ["USDT", "BUSD", "USDC"])
                self.account_balance_usd = round(usdt, 2)
                return {"status": self.status, "connected": True, "balance_usd": self.account_balance_usd}
            else:
                self.status = "AUTH_FAILED"
                return {"status": self.status, "connected": False, "message": f"Binance API Error {resp.status_code}"}
        except Exception as e:
            self.status = "CONNECTION_ERROR"
            return {"status": self.status, "connected": False, "message": str(e)}

    def save_credentials(self, api_key: str, secret_key: str, testnet: bool = False) -> Dict[str, Any]:
        """Save and cryptographically verify credentials."""
        self.api_key = api_key.strip()
        self.secret_key = secret_key.strip()
        self.testnet = testnet
        self.base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"

        config_data = {
            "api_key": self.api_key,
            "secret_key": self.secret_key,
            "testnet": self.testnet,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with open(BINANCE_CONFIG_FILE, "w") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"[BINANCE] Save config notice: {e}")

        return self.verify_connection()

    def get_account_info(self) -> Dict[str, Any]:
        return self.get_public_status()

    def get_public_status(self) -> Dict[str, Any]:
        """Return safe, secret-masked status for frontend presentation."""
        masked_key = f"{self.api_key[:4]}••••••••{self.api_key[-4:]}" if len(self.api_key) > 8 else "NOT_CONFIGURED"
        return {
            "status": self.status,
            "is_live": (self.status == "LIVE_TRADING_ACTIVE"),
            "masked_api_key": masked_key,
            "testnet": self.testnet,
            "account_balance_usd": self.account_balance_usd,
            "exchange_label": "Binance Spot & USDT-M Futures (HMAC SHA256)"
        }

# Global Singleton Binance Broker Instance
binance_broker = BinanceBroker()
