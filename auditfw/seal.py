
"""Shared-key HMAC sealing for trusted-component audit trails."""
import hashlib, hmac, json

def seal_trail(entries: list, key: bytes) -> str:
    mac = hmac.new(key, json.dumps(entries, sort_keys=True).encode(),
                   hashlib.sha256).hexdigest()
    return mac

def verify_trail(entries: list, key: bytes, mac: str) -> bool:
    return hmac.compare_digest(seal_trail(entries, key), mac)
