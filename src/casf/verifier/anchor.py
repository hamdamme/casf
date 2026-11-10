"""Explicit, independently pinned checkpoint input for suffix verification."""

from dataclasses import dataclass, field

from casf.errors import SchemaError, TrustError
from casf.model.operations import Checkpoint, WitnessResult
from casf.model.schema import DIGEST_RE
from casf.types import JsonObject


@dataclass(frozen=True, slots=True, init=False)
class VerificationAnchor:
    """Owned public evidence and its independently retained checkpoint digest.

    Construction does not authenticate signatures. The verifier checks them
    against the accepted manifest and provisioned keys before using this start.
    """
    checkpoint: Checkpoint
    _receipt: WitnessResult = field(repr=False)

    def __init__(self, checkpoint: JsonObject, receipt: JsonObject, *,
                 expected_checkpoint_hash: str) -> None:
        if not isinstance(expected_checkpoint_hash, str) or not DIGEST_RE.fullmatch(expected_checkpoint_hash):
            raise SchemaError('expected checkpoint hash must be a lowercase digest')
        cp, rc = Checkpoint(checkpoint), WitnessResult(receipt)
        if cp.checkpoint_hash != expected_checkpoint_hash:
            raise TrustError('checkpoint does not match the independently pinned hash')
        cb, rb = cp.body, rc.body
        if (rb['checkpoint_hash'] != cp.checkpoint_hash or rb['checkpoint_index'] != cp.index
                or rb['count'] != cp.count or rb['head_hash'] != cb['head_hash']
                or rb['log_id'] != cp.log_id or rb['manifest_hash'] != cb['manifest_hash']):
            raise TrustError('anchor receipt does not match the checkpoint')
        object.__setattr__(self, 'checkpoint', cp)
        object.__setattr__(self, '_receipt', rc)

    @property
    def receipt(self) -> JsonObject:
        return self._receipt.receipt
