"""Synthetic authority evidence for tests, never operational trust material."""

from casf.lifecycle import sign_status


def active_status(authority, manifest_hash):
    return sign_status(authority, serial=1, manifest_hash=manifest_hash,
                       status="active", issued_at="2026-10-11T00:00:00.000000Z", reason="")


def register_active(witness, manifest, authority):
    """Provision a test witness with its required initial active status."""
    witness.register_log(
        manifest, active_status(authority, manifest["manifest_hash"]))
