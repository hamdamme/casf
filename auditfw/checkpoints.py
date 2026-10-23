
"""Signed checkpoints anchor the chain head. A verifier holding an
out-of-band trusted checkpoint can detect suffix truncation."""
import json, time
from .chain import canonical

class CheckpointService:
    def __init__(self, signer):
        self.signer = signer
        self.checkpoints = []

    def create(self, storage, note: str = "") -> dict:
        rec = storage.checkpoint_record()
        cp = {"created_at": int(time.time()), "note": note, **rec}
        cp["signature"] = self.signer.sign(canonical(cp)).hex()
        cp["key_version"] = self.signer.active_version()
        self.checkpoints.append(cp)
        return cp

    def latest(self):
        return self.checkpoints[-1] if self.checkpoints else None
