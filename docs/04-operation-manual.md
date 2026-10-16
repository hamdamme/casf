# Operation Manual

## Installation
```bash
pip install cryptography        # only dependency
```

## 1. Initialize keys
```python
from auditfw import KeyRegistry, Signer
reg = KeyRegistry("registry.json")
reg.generate("v1")                       # first key, becomes active
reg.export_public_bundle("pubkeys.json") # give this to verifiers ONLY
signer = Signer(reg)
```

## 2. Log events
```python
from auditfw import HashChain, LogStorage
storage = LogStorage("audit.db")
chain = HashChain(storage)
chain.append(
    {"actor": "alice", "action": "login"},
    signer=signer,
    hmac_key=shared_hmac_key,            # bytes, shared with trusted peers
    key_version=reg.active_version(),
)
```

## 3. Rotate keys (scheduled or on suspicion)
```python
reg.rotate("v2")   # v1 stays in registry: old entries still verify
```
New entries use v2 immediately; historical verification is unaffected
because entries carry `key_version`.

## 4. Seal and ship a trail to a trusted component
```python
from auditfw import seal_trail, verify_trail
entries = list(storage.iter_entries())
mac = seal_trail(entries, shared_hmac_key)
# ... transfer (entries, mac) ...
assert verify_trail(entries, shared_hmac_key, mac)
```

## 5. Checkpoints (truncation defense)
```python
from auditfw import CheckpointService
cps = CheckpointService(signer)
cp = cps.create(storage)   # sign the current head
# publish cp OUT-OF-BAND (object lock storage, transparency log, etc.)
```
Run on a schedule (e.g., every 10k entries or hourly).

## 6. Encrypt logs at rest
```python
from auditfw import AtRestEncryption
enc = AtRestEncryption()   # generates a random 256-bit key
blob = enc.encrypt_log(open("events.jsonl","rb").read(), aad=b"audit")
plain = enc.decrypt_log(blob, aad=b"audit")
```
Store `enc.key` in your secrets manager, never next to the log.

## Error handling
- `TamperedError(seq, reason)` from any verify call: quarantine the
  log, alert, and do not write to the same chain until investigated.
