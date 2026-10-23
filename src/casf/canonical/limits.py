"""Input bounds from SPEC §9. Limits apply BEFORE expensive crypto work."""

from dataclasses import dataclass

SAFE_INT_MIN = -(2**53) + 1          # -9007199254740991
SAFE_INT_MAX = (2**53) - 1           #  9007199254740991

MAX_CANONICAL_BODY_BYTES = 65536     # canonical record body
MAX_WIRE_ENVELOPE_BYTES = 131072     # wire record envelope
MAX_NESTING_DEPTH = 16               # containers; the body counts as depth 1
MAX_STRING_BYTES = 32768             # per string, UTF-8 encoded
MAX_PROTOCOL_BODY_BYTES = 16384      # non-record protocol object bodies (§20)
MAX_JSONL_LINE_BYTES = 131072        # bundle import (§20)
MAX_CHECKPOINT_CHAIN_STEPS = 10000   # online traversal default (§15)
MAX_CHECKPOINT_BATCH = 128           # records per checkpoint extension (§12)
MAX_WITNESS_REQUEST_BYTES = 16 * 1024 * 1024   # §14
WITNESS_MAX_RECORDS = 128                      # §14
QUERY_TIMEOUT_SECONDS = 10                     # §14, §15

@dataclass(frozen=True)
class Limits:
    max_depth: int = MAX_NESTING_DEPTH
    max_string_bytes: int = MAX_STRING_BYTES
