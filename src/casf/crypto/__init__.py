"""Domain-separated cryptographic operations (SPEC §9-§16).

Rules enforced here:
  - H is SHA-256; signatures are pure Ed25519 (RFC 8032), via the
    maintained `cryptography` library only (never hand-rolled).
  - Every object type has its own digest domain and signature domain;
    signing and verifying use domain || raw-digest bytes.
  - Public keys are raw 32 bytes; signatures 64 bytes; digests are
    64 lowercase hex; binary wire fields are unpadded base64url.
  - Key IDs are digests of raw public keys under the key-id domain.

Verification is public-key-only: no private key material is accepted
by any function in this module.
"""

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from casf.canonical.jcs import canonicalize
from casf.errors import CasfError, SchemaError
from casf.types import JsonValue

__all__ = [
    "b64url_decode",
    "b64url_encode",
    "digest_checkpoint",
    "digest_latest",
    "digest_manifest",
    "digest_receipt",
    "digest_record",
    "digest_status",
    "generate_key",
    "genesis_hash",
    "key_id",
    "load_public_key",
    "public_key_raw",
    "sha256",
    "sign_checkpoint",
    "sign_latest",
    "sign_manifest",
    "sign_receipt",
    "sign_record",
    "sign_status",
    "verify_checkpoint",
    "verify_latest",
    "verify_manifest",
    "verify_receipt",
    "verify_record",
    "verify_status",
]

# ------------------------------------------------------------- encodings

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def _domain(name: str) -> bytes:
    return b"CASF/v1/" + name.encode("ascii") + b"\x00"

DOMAINS = {
    "key_id": _domain("key-id"),
    "manifest": _domain("manifest"),
    "manifest_sign": _domain("manifest-sign"),
    "genesis": _domain("genesis"),
    "record": _domain("record"),
    "record_sign": _domain("record-sign"),
    "request": _domain("request"),
    "checkpoint": _domain("checkpoint"),
    "checkpoint_sign": _domain("checkpoint-sign"),
    "receipt": _domain("receipt"),
    "receipt_sign": _domain("receipt-sign"),
    "latest": _domain("latest"),
    "latest_sign": _domain("latest-sign"),
    "status": _domain("status"),
    "status_sign": _domain("status-sign"),
}

def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

def b64url_decode(text: str) -> bytes:
    """Decode unpadded base64url; reject non-canonical encodings."""
    if not text or any(c not in
                       "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
                       for c in text):
        raise SchemaError("invalid base64url characters")
    if len(text) % 4 == 1:
        raise SchemaError("invalid base64url length")
    pad = "=" * (-len(text) % 4)
    try:
        raw = base64.urlsafe_b64decode(text + pad)
    except Exception as e:
        raise SchemaError("invalid base64url") from e
    if b64url_encode(raw) != text:  # canonical re-encode check (SPEC §9)
        raise SchemaError("non-canonical base64url encoding")
    return raw

# ----------------------------------------------------------------- keys

def generate_key() -> Ed25519PrivateKey:
    """Generate a signing key from OS randomness."""
    return Ed25519PrivateKey.generate()

def public_key_raw(priv: Ed25519PrivateKey) -> bytes:
    return priv.public_key().public_bytes_raw()

def load_public_key(raw: bytes) -> Ed25519PublicKey:
    if len(raw) != 32:
        raise SchemaError("Ed25519 public keys are exactly 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)

def key_id(raw_public_key: bytes) -> str:
    return sha256(DOMAINS["key_id"] + raw_public_key).hex()

# ----------------------------------------------------- sign / verify core

def _sign(priv: Ed25519PrivateKey, sign_domain: str, digest: bytes) -> str:
    sig = priv.sign(DOMAINS[sign_domain] + digest)
    return b64url_encode(sig)

def _verify(raw_public_key: bytes, sign_domain: str, digest: bytes,
            signature_b64: str) -> None:
    try:
        sig = b64url_decode(signature_b64)
    except SchemaError as e:
        raise CasfError("signature is not canonical base64url") from e
    if len(sig) != 64:
        raise CasfError("Ed25519 signatures are exactly 64 bytes")
    pub = load_public_key(raw_public_key)
    try:
        pub.verify(sig, DOMAINS[sign_domain] + digest)
    except InvalidSignature as e:
        raise CasfError(f"invalid signature under domain {sign_domain}") from e

def _hex_digest(digest_domain: str, body: JsonValue) -> str:
    return sha256(DOMAINS[digest_domain] + canonicalize(body)).hex()

# ------------------------------------------------------- object operations

def digest_manifest(body: JsonValue) -> str:
    return _hex_digest("manifest", body)

def sign_manifest(authority_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(authority_priv, "manifest_sign",
                 bytes.fromhex(digest_manifest(body)))

def verify_manifest(authority_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(authority_raw_pub, "manifest_sign",
            bytes.fromhex(digest_manifest(body)), signature_b64)

def genesis_hash(manifest_digest_hex: str) -> str:
    return sha256(DOMAINS["genesis"] + bytes.fromhex(manifest_digest_hex)).hex()

def digest_record(body: JsonValue) -> str:
    return _hex_digest("record", body)

def sign_record(log_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(log_priv, "record_sign", bytes.fromhex(digest_record(body)))

def verify_record(log_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(log_raw_pub, "record_sign",
            bytes.fromhex(digest_record(body)), signature_b64)

def request_digest(request: JsonValue) -> str:
    """Idempotency digest over the exact caller request (SPEC §11)."""
    return _hex_digest("request", request)

def digest_checkpoint(body: JsonValue) -> str:
    return _hex_digest("checkpoint", body)

def sign_checkpoint(log_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(log_priv, "checkpoint_sign",
                 bytes.fromhex(digest_checkpoint(body)))

def verify_checkpoint(log_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(log_raw_pub, "checkpoint_sign",
            bytes.fromhex(digest_checkpoint(body)), signature_b64)

def digest_receipt(body: JsonValue) -> str:
    return _hex_digest("receipt", body)

def sign_receipt(witness_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(witness_priv, "receipt_sign",
                 bytes.fromhex(digest_receipt(body)))

def verify_receipt(witness_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(witness_raw_pub, "receipt_sign",
            bytes.fromhex(digest_receipt(body)), signature_b64)

def digest_latest(body: JsonValue) -> str:
    return _hex_digest("latest", body)

def sign_latest(witness_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(witness_priv, "latest_sign",
                 bytes.fromhex(digest_latest(body)))

def verify_latest(witness_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(witness_raw_pub, "latest_sign",
            bytes.fromhex(digest_latest(body)), signature_b64)

def digest_status(body: JsonValue) -> str:
    return _hex_digest("status", body)

def sign_status(authority_priv: Ed25519PrivateKey, body: JsonValue) -> str:
    return _sign(authority_priv, "status_sign",
                 bytes.fromhex(digest_status(body)))

def verify_status(authority_raw_pub: bytes, body: JsonValue, signature_b64: str) -> None:
    _verify(authority_raw_pub, "status_sign",
            bytes.fromhex(digest_status(body)), signature_b64)
