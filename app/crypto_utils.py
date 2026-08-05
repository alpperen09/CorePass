"""
crypto_utils.py
----------------
CorePass'in şifreleme çekirdeği.

- Master parola, kullanıcıdan asla ham (plaintext) olarak diske yazılmaz.
- PBKDF2HMAC (SHA-256, 480.000 iterasyon) ile master paroladan 32 baytlık
  bir simetrik anahtar türetilir (key derivation).
- Türetilen anahtar, Fernet (AES-128-CBC + HMAC) ile kasadaki tüm hesap
  kayıtlarını şifrelemek/çözmek için kullanılır.
- Salt her kasa için rastgele üretilir ve vault_salt.bin içinde saklanır.
  Salt gizli değildir ama asla sabit (hardcoded) olmamalıdır.
"""

import base64
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 480_000
SALT_SIZE = 16


def generate_salt() -> bytes:
    """Yeni bir kasa için kriptografik olarak güvenli rastgele salt üretir."""
    return secrets.token_bytes(SALT_SIZE)


def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Master paroladan Fernet uyumlu (url-safe base64, 32 byte) bir anahtar türetir.
    Aynı parola + aynı salt her zaman aynı anahtarı üretir (deterministik).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    raw_key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


class VaultCipher:
    """Türetilmiş anahtarı kullanarak şifreleme/çözme işlemlerini yürütür."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            data = self._fernet.decrypt(token.encode("utf-8"))
            return data.decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Şifre çözülemedi: yanlış master parola veya bozuk veri.") from exc

    @staticmethod
    def verify_password(master_password: str, salt: bytes, check_token: str) -> bool:
        """
        Kasa açılırken master parolanın doğruluğunu, bilinen bir 'check_token'ı
        çözmeye çalışarak doğrular. check_token, kasa ilk oluşturulurken
        sabit bir metnin ("corepass-verify") şifrelenmiş halidir.
        """
        try:
            key = derive_key(master_password, salt)
            cipher = VaultCipher(key)
            return cipher.decrypt(check_token) == "corepass-verify"
        except Exception:
            return False


def make_verify_token(master_password: str, salt: bytes) -> str:
    """Kasa ilk oluşturulurken parola doğrulama token'ı üretir."""
    key = derive_key(master_password, salt)
    cipher = VaultCipher(key)
    return cipher.encrypt("corepass-verify")
