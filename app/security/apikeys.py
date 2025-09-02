import secrets
import hashlib


def generate_api_key() -> tuple[str, str, str]:
    plaintext_key = f"sk-{secrets.token_urlsafe(32)}"
    api_key_hash = hash_api_key(plaintext_key)
    last4 = plaintext_key[-4:]
    return plaintext_key, api_key_hash, last4


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode('utf-8')).hexdigest() 