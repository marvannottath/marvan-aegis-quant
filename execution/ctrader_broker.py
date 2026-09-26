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
        self._load_config()

    def _load_config(self):
        if CTRADER_CONFIG_FILE.exists():
            try:
                with open(CTRADER_CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    self.client_id = cfg.get("client_id", "")
                    self.client_secret = cfg.get("client_secret", "")
                    self.access_token = cfg.get("access_token", "")
                    self.account_id = cfg.get("account_id", "")
                    if self.access_token and self.account_id:
                        self.status = "CONFIGURED"
            except Exception:
                pass

    def save_credentials(self, client_id: str, client_secret: str, access_token: str, account_id: str) -> Dict[str, Any]:
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.access_token = access_token.strip()
        self.account_id = account_id.strip()

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            "account_id": self.account_id,
            "updated_at": time.time()
        }

        try:
            CTRADER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CTRADER_CONFIG_FILE, "w") as f:
                json.dump(payload, f, indent=2)
            
            return self.connect()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def connect(self) -> Dict[str, Any]:
        """Verify the OAuth token via Spotware REST API."""
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
                return {
                    "status": "SUCCESS",
                    "message": "cTrader Open API Connected Successfully!",
                    "data": data
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
