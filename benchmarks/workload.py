"""Deterministic workload generator for the benchmarks (SPEC §22).

A fixed seed reproduces the same event list, so reruns of a manifest
execute the identical procedure (T19). The generator pads each event
to a target request size and reports the honest minimum record size
measured through the real writer path instead of pretending an
impossible target was met.
"""

import random
import tempfile
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.canonical.jcs import canonicalize

ACTOR = "bench-actor"
EVENT_TYPE = "bench"
LOG_ID = "123e4567-e89b-42d3-a456-4266bbcc0000"
TS = "2026-10-11T00:00:00.000000Z"


def seeded_key(role: str) -> Ed25519PrivateKey:
    """Deterministic benchmark key; measurements never depend on it."""
    return Ed25519PrivateKey.from_private_bytes(
        sha256(f"casf-bench-{role}".encode()).digest())


def _event_id(rng: random.Random) -> str:
    hexs = f"{rng.getrandbits(128):032x}"
    return (f"{hexs[:8]}-{hexs[8:12]}-4{hexs[13:16]}-"
            f"{hexs[16:20]}-{hexs[20:32]}")


def _request(event_id: str, data: str) -> dict:
    return {"event_id": event_id, "actor": ACTOR, "event_type": EVENT_TYPE,
            "payload": {"data": data}, "attributes": {}}


def _overhead() -> int:
    return len(canonicalize(_request(_event_id(random.Random(0)), "")))


def generate(seed: int, count: int, target_bytes: int) -> list[dict]:
    """One seeded event list, padded so each request reaches the target."""
    rng = random.Random(seed)
    pad = max(0, target_bytes - _overhead())
    return [_request(_event_id(rng), "x" * pad) for _ in range(count)]


def measure_minimum() -> int:
    """Stored size of one minimal record, measured through the writer."""
    from casf.writer import Writer  # local import: writer pulls in storage

    auth, log, wit = (seeded_key(r) for r in ("authority", "log", "witness"))
    auth_pub = crypto.public_key_raw(auth)
    log_pub = crypto.public_key_raw(log)
    wit_pub = crypto.public_key_raw(wit)
    body = {
        "version": 1, "type": "manifest", "log_id": LOG_ID,
        "issuer_id": crypto.key_id(auth_pub),
        "log_key_id": crypto.key_id(log_pub),
        "log_public_key": crypto.b64url_encode(log_pub),
        "witness_id": crypto.key_id(wit_pub),
        "witness_public_key": crypto.b64url_encode(wit_pub),
        "created_at": TS, "predecessor": None,
    }
    manifest = {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": crypto.sign_manifest(auth, body),
    }
    with tempfile.TemporaryDirectory() as d:
        writer = Writer(Path(d) / "minimum.db", log)
        try:
            writer.create_log(manifest)
            writer.append(LOG_ID, **generate(seed=0, count=1,
                                             target_bytes=0)[0])
            record = next(writer.records(LOG_ID))
            return len(canonicalize(record))
        finally:
            writer.close()


def generate_with_minimum(seed: int, count: int,
                          target_bytes: int) -> tuple[list[dict], int]:
    """Events plus the honest minimum stored record size in bytes.

    When the target sits below what the fixed record fields already
    occupy, the events keep their achievable size and the caller must
    report the measured minimum rather than the target (SPEC §22).
    """
    return generate(seed, count, target_bytes), measure_minimum()
