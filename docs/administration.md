# Local CASF administration

This guide covers the explicit file based provisioning commands. Keep
authority and signing keys outside the repository. The commands refuse to
overwrite output files and create those files with owner only permissions.
The manifest and trust file contain public data, but their restricted file
permissions make accidental disclosure less likely.

## Create keys and public key files

```sh
export CASF_PASSPHRASE='use a private prompt or secret manager'
casf key generate --role authority --out authority.pem
casf key generate --role log --out log.pem
casf key generate --role witness --out witness.pem
```

Export only the public keys for provisioning. This small script decrypts the
key locally and writes public PEM files; it does not print key material:

```python
from pathlib import Path
import os
from cryptography.hazmat.primitives import serialization
from casf.keys import load_key

for role in ("authority", "log", "witness"):
    key = load_key(f"{role}.pem", passphrase=os.environ["CASF_PASSPHRASE"].encode())
    Path(f"{role}.pub.pem").write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
```

The script reads the passphrase from the current environment and never prints
it. A secret manager or protected prompt is preferable. Avoid saving it in a
shell profile or repository.

## Create a manifest and trust pins

```sh
casf admin manifest --authority-key authority.pem \
  --log-public-key log.pub.pem --witness-public-key witness.pub.pem \
  --out manifest.json
casf admin trust --manifest manifest.json \
  --authority-public-key authority.pub.pem --witness-url https://witness.example \
  --mode anchored --out trust.json
```

The authority public key used to verify the manifest must be obtained through
a channel independent of the manifest and evidence bundle. Verify the
authority and witness identities with the intended operator before relying on
the generated trust pins. The trust command checks the manifest signature;
it does not establish that the key belongs to the person or service you
intended.

## Create a status statement

```sh
casf admin status sign --manifest manifest.json --authority-key authority.pem \
  --serial 1 --status active --reason "initial provisioning" \
  --out status.json
```

Add the public statement as one canonical JSON line in a bundle's
`status.jsonl` file. Later statements must use a strictly greater serial.
Install a later statement into the local witness state as well:

```sh
casf admin status install --status-file revoked.json --log-id LOG_UUID \
  --authority-public-key authority.pub.pem --witness-key witness.pem \
  --db witness.db
```

An active statement does not establish that the authority has no newer
revocation statement elsewhere.

## Register and rotate

Register a manifest directly in the local witness database:

```sh
casf admin register --manifest manifest.json \
  --status-file status.json \
  --authority-public-key authority.pub.pem \
  --witness-key witness.pem --db witness.db
```

Create a linked successor after retaining the old final checkpoint and
receipt:

```sh
casf admin rotate --final-checkpoint final-checkpoint.json \
  --final-receipt final-receipt.json --authority-key authority.pem \
  --new-log-key next-log.pem --witness-public-key witness.pub.pem \
  --out next-manifest.json
```

The new epoch still needs a separate trust decision and witness registration.
Do not replace the old manifest or its evidence.

The reference witness blocks new submissions until an active serial 1
statement is installed, then accepts only advancing status serials. A verified
revocation is terminal and blocks new checkpoint submissions. Existing
receipts remain retrievable. Offline verifier status still cannot prove that
no newer authority statement exists elsewhere.

Append and checkpoint commands require the log private key because they sign
records or checkpoints. Export reads a consistent snapshot of the database
and does not sign; it therefore does not require a private key. See
[installation and usage](installation.md) and the
[CASF specification](specification/CASF_SPEC_001.md).
