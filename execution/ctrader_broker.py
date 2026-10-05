import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List

CTRADER_CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "ctrader_config.json"

class CTraderBrokerAdapter:
    """
    Adapter for cTrader Open API (Spotware).
    Connects to the cTrader REST/WebSocket API natively on Ubuntu.
    """
    def __init__(self):
        self.client_id: str = ""
        self.client_secret: str = ""
        self.access_token: str = ""
        self.account_id: str = ""
        self.is_connected: bool = False
        self.status: str = "NOT_CONFIGURED"
        self.balance: float = 0.0
        self.currency: str = "USD"
        self._load_config()

    def _load_config(self):
        if CTRADER_CONFIG_FILE.exists():
            try:
                with open(CTRADER_CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    self.client_id = cfg.get("client_id", "")
                    self.client_secret = cfg.get("client_secret", "")
                    self.access_token = cfg.get("access_token", "")
                    self.account_id = str(cfg.get("account_id", ""))
                    self.balance = float(cfg.get("balance", 0.0))
                    self.currency = cfg.get("currency", "USD")
                    if self.access_token and self.account_id:
                        self.status = "CONFIGURED"
            except Exception:
                pass

    def save_credentials(self, client_id: str, client_secret: str, access_token: str, account_id: str) -> Dict[str, Any]:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.access_token = access_token.strip()
        self.account_id = str(account_id).strip()

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            "account_id": self.account_id,
            "balance": self.balance,
            "currency": self.currency,
            "updated_at": time.time()
        }

        try:
            CTRADER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CTRADER_CONFIG_FILE, "w") as f:
                json.dump(payload, f, indent=2)
            
            return self.connect()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch real-time account information or cached state."""
        if self.is_connected or self.access_token:
            self.connect()
        return {
            "account_id": self.account_id,
            "balance": self.balance,
            "currency": self.currency,
            "status": self.status,
            "is_connected": self.is_connected
        }

    def connect(self) -> Dict[str, Any]:
        """Verify the OAuth token via Spotware REST API and fetch account balance."""
        if not self.access_token:
            return {"status": "ERROR", "message": "Access Token missing"}

        try:
            # Test authentication using cTrader REST API
            headers = {"Authorization": f"Bearer {self.access_token}"}
            url = f"https://api.spotware.com/connect/tradingaccounts"
            resp = requests.get(url, headers=headers, timeout=5.0)

            if resp.status_code == 200:
                data = resp.json()
                self.is_connected = True
                self.status = "CONNECTED"

                # Extract balance and currency from Spotware trading accounts response
                accounts = data if isinstance(data, list) else data.get("data", [])
                found_acc = None
                if isinstance(accounts, list):
                    for acc in accounts:
                        acc_num = str(acc.get("accountNumber") or acc.get("accountId") or acc.get("traderRegistrationId") or "")
                        if acc_num == str(self.account_id) or not self.account_id:
                            found_acc = acc
                            if not self.account_id:
                                self.account_id = acc_num
                            break
                    if not found_acc and accounts:
                        found_acc = accounts[0]
                        if not self.account_id:
                            self.account_id = str(found_acc.get("accountNumber") or found_acc.get("accountId") or "")

                if found_acc:
                    # Spotware accounts balance is typically in cents or currency units
                    raw_bal = float(found_acc.get("balance") or found_acc.get("equity") or found_acc.get("depositFunds") or 0.0)
                    money_digits = int(found_acc.get("moneyDigits") or 2)
                    if money_digits > 0 and raw_bal > 10000 and "moneyDigits" in found_acc:
                        self.balance = round(raw_bal / (10 ** money_digits), 2)
                    else:
                        self.balance = round(raw_bal, 2)
                    self.currency = found_acc.get("currency") or found_acc.get("depositAsset") or "USD"

                    # Save updated balance to file
                    try:
                        if CTRADER_CONFIG_FILE.exists():
                            with open(CTRADER_CONFIG_FILE, "r") as f:
                                cfg = json.load(f)
                            cfg["balance"] = self.balance
                            cfg["currency"] = self.currency
                            with open(CTRADER_CONFIG_FILE, "w") as f:
                                json.dump(cfg, f, indent=2)
                    except Exception:
                        pass

                return {
                    "status": "SUCCESS",
                    "message": "cTrader Open API Connected Successfully!",
                    "data": data,
                    "balance": self.balance,
                    "currency": self.currency
                }
            else:
                self.is_connected = False
                self.status = "CONNECTION_FAILED"
                return {"status": "ERROR", "message": f"cTrader API Auth Failed: {resp.text}"}
                
        except Exception as e:
            self.is_connected = False
            self.status = "CONNECTION_FAILED"
            return {"status": "ERROR", "message": f"Network Error: {e}"}

# Global singleton
ctrader_broker = CTraderBrokerAdapter()
