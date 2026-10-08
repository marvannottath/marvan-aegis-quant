"""
Aegis-Quant Account-Scoped Cache Engine.
Enforces strict namespace isolation across all accounts:
- positions:{account_id}
- equity:{account_id}
- pnl:{account_id}
- signals:{account_id}
- vault:{account_id}
- performance:{account_id}
- market:{account_id}

Rules:
- No global unscoped financial/trading cache.
- Automatic invalidation on account switch or state mutation.
- Stale cache from another account is NEVER rendered.
"""

import time
from typing import Dict, Any, Optional, Set, Callable
from threading import Lock

class AccountScopedCache:
    """Thread-safe, account-isolated cache container with TTL and explicit invalidation."""

    def __init__(self, default_ttl_seconds: float = 5.0):
        self._default_ttl = default_ttl_seconds
        # key format: "{namespace}:{account_id}" -> {"data": Any, "expires_at": float, "updated_at": float}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._active_account_id: Optional[str] = None

    def _build_key(self, namespace: str, account_id: str, environment: Optional[str] = None) -> str:
        if not account_id:
            raise ValueError("ACCOUNT_CACHE_ERROR: account_id cannot be empty")
        env_str = str(environment).strip().upper() if environment else None
        if not env_str:
            try:
                from core.account_context import account_context_manager
                acc = account_context_manager.get_account(account_id.strip())
                if acc:
                    env_str = acc.environment
            except Exception:
                pass
        env_str = "PAPER" if env_str in ("DEMO", "TESTNET", "SANDBOX") else (env_str or "PAPER")
        return f"{namespace}:{env_str}:{account_id.strip()}"

    def set(
        self,
        namespace: str,
        account_id: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
        environment: Optional[str] = None
    ):
        """Set environment-and-account scoped cached data with TTL."""
        key = self._build_key(namespace, account_id, environment)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            self._cache[key] = {
                "data": value,
                "expires_at": time.time() + ttl,
                "updated_at": time.time(),
                "account_id": account_id,
                "environment": key.split(":")[1] if ":" in key else "PAPER",
                "namespace": namespace
            }

    def get(self, namespace: str, account_id: str, environment: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve environment-and-account scoped cached data.
        Returns None if key missing, expired, or belonging to another environment/account.
        """
        key = self._build_key(namespace, account_id, environment)
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if time.time() > entry["expires_at"]:
                # Expired - remove and return None
                del self._cache[key]
                return None
            return entry["data"]

    def invalidate_account(self, account_id: str, environment: Optional[str] = None):
        """Invalidate all cached namespaces for a specific account (and optional environment)."""
        with self._lock:
            if environment:
                env_str = str(environment).strip().upper()
                norm_env = "PAPER" if env_str in ("DEMO", "TESTNET", "SANDBOX") else env_str
                suffix = f":{norm_env}:{account_id.strip()}"
                keys_to_delete = [k for k in self._cache.keys() if k.endswith(suffix)]
            else:
                suffix = f":{account_id.strip()}"
                keys_to_delete = [k for k in self._cache.keys() if k.endswith(suffix)]
            for k in keys_to_delete:
                del self._cache[k]

    def invalidate_environment(self, environment: str):
        """Invalidate all cached keys for a specific environment."""
        env_str = str(environment).strip().upper()
        norm_env = "PAPER" if env_str in ("DEMO", "TESTNET", "SANDBOX") else env_str
        with self._lock:
            prefix = f":{norm_env}:"
            keys_to_delete = [k for k in self._cache.keys() if prefix in k]
            for k in keys_to_delete:
                del self._cache[k]

    def switch_account(self, new_account_id: str, previous_account_id: Optional[str] = None, environment: Optional[str] = None):
        """
        Handle account switch sequence:
        1. Invalidate previous account cache if requested
        2. Set active account ID
        """
        with self._lock:
            if previous_account_id and previous_account_id != new_account_id:
                suffix = f":{previous_account_id.strip()}"
                keys_to_delete = [k for k in self._cache.keys() if k.endswith(suffix)]
                for k in keys_to_delete:
                    del self._cache[k]
            self._active_account_id = new_account_id

    def clear_all(self):
        """Clear all cache."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            active_keys = [k for k, v in self._cache.items() if v["expires_at"] > now]
            return {
                "total_cached_entries": len(self._cache),
                "active_non_expired_entries": len(active_keys),
                "active_account_id": self._active_account_id
            }


# Global singleton
account_cache = AccountScopedCache()
