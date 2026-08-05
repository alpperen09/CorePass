"""
vault.py
--------
CorePass kasasının veri katmanı.

Disk üzerinde iki dosya tutulur:
  - vault_salt.bin  -> PBKDF2 için salt (şifreli değil, gizli değil)
  - vault.enc       -> JSON yapısındaki kayıtların Fernet ile şifrelenmiş hali

Kasadaki her hesap kaydı şu alanları içerir:
  id, site, username, password, notes, created_at
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from crypto_utils import (
    VaultCipher,
    derive_key,
    generate_salt,
    make_verify_token,
)

VAULT_DIR = os.path.join(os.path.expanduser("~"), ".corepass")
SALT_PATH = os.path.join(VAULT_DIR, "vault_salt.bin")
VAULT_PATH = os.path.join(VAULT_DIR, "vault.enc")
VERIFY_TOKEN_PATH = os.path.join(VAULT_DIR, "vault_verify.token")


class Vault:
    """Bellek içinde açık (decrypted) kasa durumunu yöneten sınıf."""

    def __init__(self):
        self.cipher: Optional[VaultCipher] = None
        self.entries: List[dict] = []
        self.is_unlocked: bool = False

    # ------------------------------------------------------------------ #
    # Kasa yaşam döngüsü
    # ------------------------------------------------------------------ #

    @staticmethod
    def vault_exists() -> bool:
        return os.path.exists(VAULT_PATH) and os.path.exists(SALT_PATH)

    def create_vault(self, master_password: str) -> None:
        """İlk kurulumda yeni, boş ve şifreli bir kasa oluşturur."""
        os.makedirs(VAULT_DIR, exist_ok=True)

        salt = generate_salt()
        with open(SALT_PATH, "wb") as f:
            f.write(salt)

        verify_token = make_verify_token(master_password, salt)
        with open(VERIFY_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(verify_token)

        key = derive_key(master_password, salt)
        self.cipher = VaultCipher(key)
        self.entries = []
        self.is_unlocked = True
        self._save()

    def unlock(self, master_password: str) -> bool:
        """Var olan bir kasayı master parola ile açar. Başarılıysa True döner."""
        if not self.vault_exists():
            return False

        with open(SALT_PATH, "rb") as f:
            salt = f.read()
        with open(VERIFY_TOKEN_PATH, "r", encoding="utf-8") as f:
            verify_token = f.read()

        if not VaultCipher.verify_password(master_password, salt, verify_token):
            return False

        key = derive_key(master_password, salt)
        self.cipher = VaultCipher(key)
        self._load()
        self.is_unlocked = True
        return True

    def lock(self) -> None:
        """Kasayı bellekte kilitler (hassas veriyi temizler)."""
        self.cipher = None
        self.entries = []
        self.is_unlocked = False

    # ------------------------------------------------------------------ #
    # CRUD işlemleri
    # ------------------------------------------------------------------ #

    def add_entry(self, site: str, username: str, password: str, notes: str = "") -> dict:
        self._require_unlocked()
        entry = {
            "id": str(uuid.uuid4()),
            "site": site,
            "username": username,
            "password": password,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.entries.append(entry)
        self._save()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        self._require_unlocked()
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        deleted = len(self.entries) != before
        if deleted:
            self._save()
        return deleted

    def list_entries(self) -> List[dict]:
        self._require_unlocked()
        return list(self.entries)

    # ------------------------------------------------------------------ #
    # Dahili şifreli okuma/yazma
    # ------------------------------------------------------------------ #

    def _save(self) -> None:
        self._require_unlocked()
        plaintext = json.dumps(self.entries, ensure_ascii=False)
        encrypted = self.cipher.encrypt(plaintext)
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            f.write(encrypted)

    def _load(self) -> None:
        if not os.path.exists(VAULT_PATH):
            self.entries = []
            return
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            encrypted = f.read()
        if not encrypted:
            self.entries = []
            return
        plaintext = self.cipher.decrypt(encrypted)
        self.entries = json.loads(plaintext)

    def _require_unlocked(self) -> None:
        if not self.is_unlocked or self.cipher is None:
            raise PermissionError("Kasa kilitli. Önce master parola ile açılmalı.")
