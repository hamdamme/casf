# Verification Manual

## CLI
```bash
python -m auditfw.cli       --log events.jsonl       --pubkeys pubkeys.json       [--hmac-key <hex>]       [--checkpoint checkpoint.json]
```
| Exit code | Meaning |
|---|---|
| 0 | chain intact; prints entry count and head hash |
| 1 | tampered; prints first broken seq and reason |
| 2 | operational error (bad file, bad key, etc.) |

## What each check proves
| Check | Detects |
|---|---|
| `prev_hash` linkage | deletion, insertion, reordering |
| `entry_hash` recompute | in-place content modification |
| HMAC | tampering by parties without the shared key |
| Ed25519 signature | forgery; identifies key version (attribution) |
| checkpoint head match | suffix truncation since checkpoint |

## Library use
```python
import json
from auditfw import Verifier
pub = json.load(open("pubkeys.json"))
v = Verifier(pub, hmac_key=b"...", trusted_checkpoint=cp)
result = v.verify_file("events.jsonl")   # or v.verify_entries(list)
```

## Acceptance test procedure
1. Generate a log of >=3 entries, with at least one key rotation.
   Expect: exit 0.
2. Edit any `payload` field. Expect: exit 1 at that seq,
   "entry hash mismatch".
3. Delete the last entry WITHOUT a checkpoint. Expect: exit 0
   (expected — checkpoints exist to catch truncation).
4. Repeat 3 WITH a checkpoint. Expect: exit 1, "head does not match
   trusted checkpoint".
5. Swap two entries. Expect: exit 1, "prev_hash mismatch".
6. Flip one hex digit in any `hmac`. Expect: exit 1, "HMAC mismatch".
7. Re-sign an entry with the wrong key version. Expect: exit 1,
   "signature invalid".
8. All tests pass => framework accepted.
