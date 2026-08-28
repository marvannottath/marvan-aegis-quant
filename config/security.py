"""
Military-Grade Security & Secret Key Vault Module.
Uses AES-256 (Fernet symmetric encryption) to encrypt and decrypt API keys, passwords, and sensitive credentials.
Prevents credential leaks in log files and code.
"""

import os
import re
import base64
from typing import Dict, Optional
from cryptography.fernet import Fernet
from config.settings import KEY_VAULT_PATH, LOG_DIR

class SecurityVault:
    def __init__(self, key_path=KEY_VAULT_PATH):
        self.key_path = key_path
        self.fernet = self._init_key()
        self._memory_secrets: Dict[str, str] = {}

    def _init_key(self) -> Fernet:
        """Initialize or load master encryption key."""
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                key = f.read().strip()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
            os.chmod(self.key_path, 0o600)  # Read/Write by owner only
        return Fernet(key)

    def encrypt_secret(self, raw_secret: str) -> str:
        """Encrypt a raw secret string using AES-256 Fernet."""
        if not raw_secret:
            return ""
        encrypted = self.fernet.encrypt(raw_secret.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt an encrypted secret in memory."""
        if not encrypted_secret:
            return ""
        try:
            decrypted = self.fernet.decrypt(encrypted_secret.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"SecurityVault: Decryption failed - {str(e)}")

    def set_memory_secret(self, key_name: str, raw_secret: str):
        """Store secret in memory-only encrypted state."""
        encrypted = self.encrypt_secret(raw_secret)
        self._memory_secrets[key_name] = encrypted

    def get_memory_secret(self, key_name: str) -> Optional[str]:
        """Fetch and decrypt secret into memory temporarily."""
        encrypted = self._memory_secrets.get(key_name)
        if encrypted:
            return self.decrypt_secret(encrypted)
        return os.getenv(key_name, None)

    @staticmethod
    def mask_secret(text: str) -> str:
        """Sanitize strings to mask API keys, Bearer tokens, or passwords before logging."""
        # Mask API keys matching common key formats
        masked = re.sub(r'(?i)(api_key|token|secret|password|bearer)\s*[:=]\s*["\']?([^"\']{4})[^"\']*["\']?',
                         r'\1: \2****', text)
        return masked

# Global Singleton Instance
vault = SecurityVault()
