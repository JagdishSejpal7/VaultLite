"""Offline license keys signed with Ed25519.
The app only holds the PUBLIC key, so customers cannot create keys for themselves.
Only the private key in SELLER_ONLY/ (never shipped) can sign valid keys."""
import base64, json, os
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from license_pub import PUBLIC_KEY_HEX

PREFIX = "VLT1-"

def verify_key(key_text):
    """Return the license dict (name, email, ...) if the key is genuine, else None."""
    try:
        key_text = "".join(key_text.split())
        if not key_text.startswith(PREFIX):
            return None
        payload_b64, sig_b64 = key_text[len(PREFIX):].split(".")
        pad = lambda s: s + "=" * (-len(s) % 4)
        payload = base64.urlsafe_b64decode(pad(payload_b64))
        sig = base64.urlsafe_b64decode(pad(sig_b64))
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX)).verify(sig, payload)
        return json.loads(payload)
    except (ValueError, InvalidSignature, KeyError, TypeError):
        return None

def load_license(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return verify_key(f.read())

def save_license(path, key_text):
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(key_text.split()))
