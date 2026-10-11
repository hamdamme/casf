
"""AES-256-GCM encryption at rest. Random 96-bit nonces: safe under the
birthday bound for any realistic volume; keys are versioned separately."""
import json, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class AtRestEncryption:
    def __init__(self, key: bytes = None):
        self.key = key or AESGCM.generate_key(bit_length=256)
        self.aes = AESGCM(self.key)

    def encrypt_log(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return nonce + self.aes.encrypt(nonce, plaintext, aad)

    def decrypt_log(self, blob: bytes, aad: bytes = b"") -> bytes:
        return self.aes.decrypt(blob[:12], blob[12:], aad)
