
"""Independent verification — trusts only the public-key bundle, never
the logging system itself."""
import hashlib, hmac, json
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from .chain import canonical, entry_digest

def _signed_body(e):
    # HMAC covers entry_hash too (it is computed before sealing);
    # the signature covers the same body (computed before signing).
    return {k: v for k, v in e.items() if k not in ("hmac", "signature")}

class TamperedError(Exception):
    def __init__(self, seq, reason):
        self.seq, self.reason = seq, reason
        super().__init__(f"chain broken at seq={seq}: {reason}")

class Verifier:
    def __init__(self, public_bundle: dict, hmac_key: bytes = None,
                 trusted_checkpoint: dict = None):
        self.pub = {v: serialization.load_pem_public_key(p.encode())
                    for v, p in public_bundle.items()}
        self.hmac_key = hmac_key
        self.checkpoint = trusted_checkpoint

    def verify_file(self, path: str) -> dict:
        entries = [json.loads(l) for l in open(path) if l.strip()]
        return self.verify_entries(entries)

    def verify_entries(self, entries: list) -> dict:
        prev = "GENESIS"
        for e in entries:
            if e["prev_hash"] != prev:
                raise TamperedError(e["seq"], "prev_hash mismatch")
            if entry_digest(e) != e["entry_hash"]:
                raise TamperedError(e["seq"], "entry hash mismatch")
            body = _signed_body(e)
            if self.hmac_key and not hmac.compare_digest(
                    hmac.new(self.hmac_key, canonical(body),
                             hashlib.sha256).hexdigest(), e.get("hmac", "")):
                raise TamperedError(e["seq"], "HMAC mismatch")
            if e.get("signature"):
                try:
                    self.pub[e["key_version"]].verify(
                        bytes.fromhex(e["signature"]), canonical(body))
                except InvalidSignature:
                    raise TamperedError(e["seq"], "signature invalid")
            prev = e["entry_hash"]
        if self.checkpoint:
            head = entries[-1] if entries else None
            if (not head or head["seq"] != self.checkpoint["head_seq"]
                    or head["entry_hash"] != self.checkpoint["head_hash"]):
                raise TamperedError(head["seq"] if head else 0,
                                    "head does not match trusted checkpoint")
        return {"status": "OK", "entries": len(entries),
                "head_hash": prev}
