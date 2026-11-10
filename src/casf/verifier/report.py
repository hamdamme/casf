"""Public verification report types and versioned diagnostic serialization."""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

from casf.types import JsonObject


class Mode(str, Enum):
    INTEGRITY = "integrity"
    ANCHORED = "anchored"
    ONLINE = "online"


class Result(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class FreshnessStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    FRESH_WITNESS_VIEW = "FRESH_WITNESS_VIEW"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONFLICT = "CONFLICT"


class TrustStatus(str, Enum):
    TRUSTED = "TRUSTED"
    UNKNOWN = "UNKNOWN"
    REVOKED = "REVOKED"
    CONFLICT = "CONFLICT"
    OK = TRUSTED
    UNTRUSTED = CONFLICT


class AnchorStatus(str, Enum):
    NONE = "NONE"
    MATCHED = "MATCHED"
    NOT_REQUESTED = NONE
    OK = MATCHED
    INCOMPLETE = "INCOMPLETE"
    DIVERGENT = "DIVERGENT"
    PARTIAL_ANCHOR = "PARTIAL_ANCHOR"


class ProtocolStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"


class Dimension(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NOT_CHECKED = "NOT_CHECKED"
    OK = VALID
    FAIL = INVALID


@dataclass(frozen=True)
class TrustPins:
    """Independently provisioned trust material (SPEC §10, §15)."""
    authority_keys: dict[str, bytes]   # issuer_id -> raw public key
    witness_keys: dict[str, bytes]     # witness_id -> raw public key
    log_id: str
    manifest_hash: str | None = None   # expected manifest digest, if pinned
    minimum_status_serial: int = 1


@dataclass
class Report:
    mode: Mode
    result: Result
    protocol_status: ProtocolStatus
    signature_status: Dimension
    chain_status: Dimension
    trust_status: TrustStatus
    anchor_status: AnchorStatus
    verified_from: int
    verified_through: int
    unwitnessed_count: int | None
    witnessed_through: int | None
    first_failure_seq: int | None
    diagnostic_codes: list[str] = field(default_factory=list)
    freshness_status: FreshnessStatus = FreshnessStatus.NOT_REQUESTED
    observed_status_serial: int = 0
    checkpoint: tuple[int, str] | None = None
    assumptions: JsonObject = field(default_factory=dict)

    @property
    def overall(self) -> Result:
        """SPEC verdict; result remains the Python compatibility field."""
        return self.result

    def to_dict(self) -> JsonObject:
        """Return a detached JSON-compatible view of every diagnostic field."""
        return {
            "report_version": 2, "mode": self.mode.value,
            "overall": self.overall.value, "result": self.result.value,
            "protocol_status": self.protocol_status.value,
            "signature_status": self.signature_status.value,
            "chain_status": self.chain_status.value, "trust_status": self.trust_status.value,
            "anchor_status": self.anchor_status.value, "freshness_status": self.freshness_status.value,
            "verified_from": self.verified_from, "verified_through": self.verified_through,
            "witnessed_through": self.witnessed_through, "unwitnessed_count": self.unwitnessed_count,
            "first_failure_seq": self.first_failure_seq,
            "diagnostic_codes": [code for code in self.diagnostic_codes],
            "observed_status_serial": self.observed_status_serial,
            "checkpoint_index": self.checkpoint[0] if self.checkpoint is not None else None,
            "checkpoint_hash": self.checkpoint[1] if self.checkpoint is not None else None,
            "assumptions": deepcopy(self.assumptions),
        }
