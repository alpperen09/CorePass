"""
api.py
------
CorePass masaüstü uygulaması içinde arka planda çalışan, SADECE localhost
(127.0.0.1) üzerinden erişilebilen hafif bir Flask API.

Chrome eklentisi bu API'ye bağlanarak:
  - Kasa kilit durumunu sorgular (/status)
  - Kayıtlı hesapları listeler (/entries)
  - Tek tıkla yeni şifre üretir (/generate)

Güvenlik notları:
  - Sunucu SADECE 127.0.0.1'e bind edilir, ağdaki başka cihazlardan erişilemez.
  - Her istek, GUI açılışında üretilen rastgele bir session token'ı
    (X-CorePass-Token header'ı) ile doğrulanmalıdır.
  - CORS sadece Chrome eklentisinin origin'ine (chrome-extension://) izin verir.
"""

import secrets
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS

from password_generator import estimate_strength, generate_password

app = Flask(__name__)
# Not: Prod ortamda extension ID'nizi sabitleyip origin'i daraltabilirsiniz.
CORS(app, resources={r"/*": {"origins": "chrome-extension://*"}})

# main.py tarafından enjekte edilen paylaşılan durum (shared state)
_vault_ref = {"vault": None}
SESSION_TOKEN = secrets.token_hex(24)


def bind_vault(vault_instance) -> None:
    """main.py, GUI ile paylaşılan Vault örneğini API'ye bağlar."""
    _vault_ref["vault"] = vault_instance


def _check_auth() -> bool:
    token = request.headers.get("X-CorePass-Token", "")
    return secrets.compare_digest(token, SESSION_TOKEN)


@app.before_request
def _enforce_auth():
    # /status/token isteği token paylaşımı için istisnadır (eşleştirme adımı)
    if request.path == "/pair":
        return None
    if not _check_auth():
        return jsonify({"error": "unauthorized", "message": "Geçersiz veya eksik CorePass token."}), 401


@app.route("/pair", methods=["POST"])
def pair():
    """
    Eklenti ilk kez bağlanırken kullanıcının GUI'de gördüğü eşleştirme kodunu
    girmesiyle çağrılır. Doğru kodu gönderirse session token'ı döner.
    """
    data = request.get_json(silent=True) or {}
    pairing_code = data.get("pairing_code", "")
    if secrets.compare_digest(pairing_code, SESSION_TOKEN[:8]):
        return jsonify({"token": SESSION_TOKEN})
    return jsonify({"error": "invalid_code"}), 403


@app.route("/status", methods=["GET"])
def status():
    vault = _vault_ref["vault"]
    unlocked = bool(vault and vault.is_unlocked)
    return jsonify({"unlocked": unlocked})


@app.route("/entries", methods=["GET"])
def list_entries():
    vault = _vault_ref["vault"]
    if not vault or not vault.is_unlocked:
        return jsonify({"error": "vault_locked"}), 423

    # Eklentiye şifreler AÇIK metin gönderilir çünkü kullanıcı 'doldur/kopyala'
    # eylemini gerçekleştirecektir; iletişim yalnızca localhost üzerinde kalır.
    entries = [
        {
            "id": e["id"],
            "site": e["site"],
            "username": e["username"],
            "password": e["password"],
        }
        for e in vault.list_entries()
    ]
    return jsonify({"entries": entries})


@app.route("/entries", methods=["POST"])
def add_entry():
    """
    Chrome eklentisi, bir form gönderiminden sonra kullanıcı onaylarsa
    yeni hesabı bu uç nokta üzerinden kasaya ekler.
    """
    vault = _vault_ref["vault"]
    if not vault or not vault.is_unlocked:
        return jsonify({"error": "vault_locked"}), 423

    data = request.get_json(silent=True) or {}
    site = (data.get("site") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not site or not username or not password:
        return jsonify({"error": "missing_fields", "message": "site, username ve password zorunludur."}), 400

    entry = vault.add_entry(site, username, password)
    return jsonify({"entry": {"id": entry["id"], "site": entry["site"], "username": entry["username"]}}), 201


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    length = int(data.get("length", 16))
    pwd = generate_password(
        length=length,
        use_uppercase=data.get("uppercase", True),
        use_lowercase=data.get("lowercase", True),
        use_digits=data.get("digits", True),
        use_symbols=data.get("symbols", True),
    )
    return jsonify({"password": pwd, "strength": estimate_strength(pwd)})


def run_api_server(host: str = "127.0.0.1", port: int = 5732) -> threading.Thread:
    """Flask API'yi arka planda ayrı bir thread üzerinde başlatır."""
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    return thread
