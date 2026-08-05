"""
password_generator.py
----------------------
Kriptografik olarak güvenli (secrets modülü tabanlı) rastgele şifre üretici.
random modülü YERİNE secrets kullanılır çünkü secrets, CSPRNG (kriptografik
olarak güvenli rastgele sayı üreteci) sağlar.
"""

import secrets
import string


AMBIGUOUS_CHARS = "il1Lo0O"  # Görsel olarak karışabilen karakterler


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """
    Belirtilen kurallara göre rastgele, güçlü bir şifre üretir.
    En az bir karakter seti seçili olmak zorundadır.
    """
    pools = []
    if use_uppercase:
        pools.append(string.ascii_uppercase)
    if use_lowercase:
        pools.append(string.ascii_lowercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{};:,.<>?")

    if not pools:
        raise ValueError("En az bir karakter seti seçilmelidir (büyük/küçük harf, rakam, sembol).")

    if exclude_ambiguous:
        pools = ["".join(c for c in pool if c not in AMBIGUOUS_CHARS) for pool in pools]

    full_pool = "".join(pools)
    if length < len(pools):
        length = len(pools)  # Her setten en az 1 karakter garanti edebilmek için

    # Her seçili karakter setinden en az bir karakter garanti et
    password_chars = [secrets.choice(pool) for pool in pools]

    # Kalan karakterleri tüm havuzdan rastgele doldur
    remaining = length - len(password_chars)
    password_chars += [secrets.choice(full_pool) for _ in range(remaining)]

    # Karakterlerin sırasını karıştır (Fisher-Yates tabanlı secrets.SystemRandom)
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def estimate_strength(password: str) -> str:
    """Basit bir sezgisel (heuristic) şifre gücü tahmini döndürür."""
    score = 0
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()-_=+[]{};:,.<>?" for c in password):
        score += 1

    if score <= 2:
        return "Zayıf"
    elif score <= 4:
        return "Orta"
    else:
        return "Güçlü"
