
"""Hash-chained, tamper-evident log engine.

Each entry embeds the SHA-256 hash of the previous entry's canonical
encoding, forming an append-only chain. Truncation attacks are
mitigated by signed checkpoints of the chain head.
"""
import hashlib, json, time, uuid

CANONICAL_SEP = (",", ":")

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=CANONICAL_SEP).encode()

def entry_digest(entry: dict) -> str:
    """SHA-256 over the entry's canonical form (excluding derived fields)."""
    body = {k: v for k, v in entry.items()
            if k not in ("hmac", "signature", "entry_hash")}
    return hashlib.sha256(canonical(body)).hexdigest()

def sealed_body(entry: dict) -> dict:
    """The exact bytes protected by HMAC and signature: all fields
    except the MAC and signature themselves. Writer and verifier
    must agree on this definition."""
    return {k: v for k, v in entry.items() if k not in ("hmac", "signature")}

class HashChain:
    def __init__(self, storage, clock=None):
        self.storage = storage
        self.clock = clock or time.time

    def append(self, payload: dict, signer=None, hmac_key: bytes = None,
               key_version: str = None, event_id: str = None) -> dict:
        seq, prev_hash = self.storage.next_seq_and_prev()
        entry = {
            "seq": seq,
            "event_id": event_id or str(uuid.uuid4()),
            "timestamp": int(self.clock() * 1000),  # bound into the signature
            "payload": payload,
            "prev_hash": prev_hash,
            "key_version": key_version,
        }
        entry["entry_hash"] = entry_digest(entry)
        body = sealed_body(entry)
        if hmac_key:
            import hmac as hmac_mod
            entry["hmac"] = hmac_mod.new(
                hmac_key, canonical(body), hashlib.sha256).hexdigest()
        if signer:
            entry["signature"] = signer.sign(canonical(body), version=key_version).hex()
        self.storage.insert(entry)
        return entry
