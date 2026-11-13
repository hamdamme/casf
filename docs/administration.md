# Local CASF administration

This guide tracks development source. The [line-review corrections](release/line-review-2026-11-11.md),
including strict key storage and predecessor registration options, are not in
the published `0.1.0rc2` wheel. Use the development setup and explicit source
commands in [installation](installation.md) when checking those changes.

This guide covers the explicit file based provisioning commands. Keep
authority and signing keys outside the repository. The commands refuse to
overwrite output files and create those files with owner only permissions.
The manifest and trust file contain public data, but their restricted file
permissions make accidental disclosure less likely.

Commands assume the environment described in [installation](installation.md).
For a complete synthetic walkthrough, including service setup, see the
[runnable demo](demo.md). The values below describe operator-provisioned files;
they are not a copy-and-run deployment configuration.

## Create keys and public key files

```bash
mkdir -m 700 casf-admin
cd casf-admin
printf 'Key passphrase: '
IFS= read -r -s CASF_PASSPHRASE
printf '\n'
export CASF_PASSPHRASE
casf key generate --role authority --out authority.pem
casf key generate --role log --out log.pem
casf key generate --role witness --out witness.pem
```

The key provider requires an owner-only key directory and regular, owner-only
key files. It rejects symlinks and oversized input. Move existing keys into a
private directory and set their permissions to `600` before loading them.
Key creation publishes a completely written, flushed file without overwriting
an existing destination. A reported storage failure requires inspecting the
destination before retrying; it may have occurred after publication.

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

Trust settings are checked before use. `allow_unwitnessed` must be a JSON
boolean, not a string or number. Mode must be `integrity`, `anchored` or
`online`; chain budgets and minimum status serials must be positive safe
integers. Manifest and witness pins must be lowercase SHA-256 digests.
Malformed settings fail before accepted verifier state is saved.

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

Witness status installation accepts only `active` or `revoked`. Unsupported
values raise `SchemaError` (CLI exit 2) before a database transaction begins;
the previously retained status is unchanged and the value is not echoed.

An active statement does not establish that the authority has no newer
revocation statement elsewhere.

## Use pins with writer commands

Create the active status statement above, register the manifest with the
witness using the registration command below, and start the witness service
before initialization. Keep the bearer token in `CASF_WITNESS_TOKEN`, not a
command argument. Create an owner-only directory for retained state, separate
from database backups:

```sh
mkdir -m 700 retained
casf init --manifest manifest.json --db writer.db --key log.pem \
  --trust trust.json --status-file status.json --state retained/writer.json \
  --initialize-state
casf append --db writer.db --key log.pem --event event.json \
  --trust trust.json --status-file status.json --state retained/writer.json
casf checkpoint --db writer.db --key log.pem \
  --trust trust.json --status-file status.json --state retained/writer.json
casf witness submit --db writer.db --key log.pem --url https://witness.example \
  --trust trust.json --status-file status.json --state retained/writer.json
casf export --db writer.db --out bundle --trust trust.json
```

`seal` requires the same trust, status and retained-state options. Writing
commands verify local history, active signed status and a fresh witness view
before signing. Initialization witnesses an empty checkpoint first. A failed
bootstrap retains its exact pending bytes; retry with a normal writing command
and the same trust/state after restoring service. Omit `--initialize-state`
once an entry exists. A missing or damaged established state file requires
recovery of that trusted state, not blind reinitialization.

Revocation and status serials persist outside the database. Revocation cannot
be undone by a later active statement, and an old open verified writer rejects
newly retained revocation or a higher status serial. Missing status/trust fails
with exit 3; unavailable witness evidence fails with exit 4. Signing remains
blocked after failed promotion. `status` and keyless export remain available
for inspection.

Default writing commands no longer silently use local-only validation.
`--local-only` explicitly selects compatibility operation; it cannot be mixed
with startup status/state options. JSON output reports `startup_verified`;
human output names the selected behavior. Supplied `--trust` pins still apply
in local-only mode, but status and freshness authorization do not.

Retain the highest checkpoint and serial independently of writer snapshots.
Fresh startup does not mean the next appended record is witnessed: checkpoint
submission remains explicit. See [writer recovery](writer-recovery.md) for the
Python API and failure semantics.

## Restore an exported bundle

Keep the expected trust pins and signed external checkpoint/receipt pair
separate from the backup. Include authentic authority statements in the
bundle's `status.jsonl`, and retain the highest known status serial in the
trust file's `minimum_status_serial` before restoring:

```sh
casf restore bundle --db restored.db --key log.pem --trust trust.json \
  --anchor-checkpoint retained-checkpoint.json \
  --anchor-receipt retained-receipt.json --json
```

The command requires an unused destination, independent pins, active signed
status and a signed anchor pair. It performs offline authentication regardless
of the trust file's verifier mode; it does not query the witness. Success
reports `restored: true` and `freshness_checked: false`. Missing or rejected
trust returns exit 3; malformed input returns 2 and invalid evidence returns 1.
An existing destination is preserved and returns 5. A restore behind the
anchor retains a sealed database, reports `RESTORE_BEHIND_WITNESS`, and returns
4. A normal writing command with the trust, status and retained-state options
performs verified startup before promoting the restored copy.

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
casf key generate --role log --out next-log.pem
casf admin rotate --old-manifest manifest.json \
  --final-checkpoint final-checkpoint.json \
  --final-receipt final-receipt.json --authority-key authority.pem \
  --new-log-key next-log.pem --witness-public-key witness.pub.pem \
  --out next-manifest.json
```

The new epoch still needs a separate trust decision and witness registration.
Do not replace the old manifest or its evidence.

Registration verifies the predecessor's authority-signed manifest, final
checkpoint, witness receipt and matching identities/counts. If this witness
already retains that evidence, it is loaded from its database. Otherwise,
provide all three files with `--predecessor-manifest`,
`--predecessor-checkpoint` and `--predecessor-receipt`. If the old authority
differs, also supply its independently obtained key through
`--predecessor-authority-public-key`. Evidence files alone never authorize a
new authority. Missing or invalid predecessor evidence prevents registration.

The Python `StatusBook` compatibility API also requires an owner-only parent
directory and file. It locks and rereads the file on every operation, preserves
terminal revocation, and flushes updates before atomic replacement. Its stored
JSON format is unchanged. Existing files with broader permissions must be
protected before use; malformed state must be recovered from trusted evidence.

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
