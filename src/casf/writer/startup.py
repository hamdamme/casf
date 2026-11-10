"""Verified write authorization and independently retained status (ADR-008)."""

import math
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Concatenate, cast

from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import CasfError, SchemaError, TrustError
from casf.online import LatestView
from casf.trust.state import StateTransaction, locked_state
from casf.types import JsonObject
from casf.verifier import Result, TrustStatus, verify
from casf.writer.recovery import hold_writer, reconcile_witness

if TYPE_CHECKING:
    from casf.writer import Writer


@dataclass(frozen=True)
class StartupPolicy:
    state_path: str | Path
    status_envelopes: tuple[JsonObject, ...]
    witness_url: str
    token: str = field(repr=False)
    initialize_state: bool = False
    timeout: float = 10.0
    max_chain_steps: int = 10_000

    def copied(self) -> "StartupPolicy":
        if type(self.initialize_state) is not bool:
            raise SchemaError("initialize_state must be boolean")
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) \
                or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise SchemaError("startup timeout must be positive and finite")
        if type(self.max_chain_steps) is not int \
                or not 1 <= self.max_chain_steps <= SAFE_INT_MAX:
            raise SchemaError("startup chain budget must be a positive safe integer")
        statuses = tuple(cast(JsonObject, parse(canonicalize(env)))
                         for env in self.status_envelopes)
        return replace(self, state_path=Path(self.state_path).absolute(), status_envelopes=statuses)


def _state_path(writer: "Writer", policy: StartupPolicy) -> str:
    path = Path(policy.state_path).resolve()
    database = Path(writer._db.path).resolve()
    reserved = {str(database) + suffix for suffix in ("", "-wal", "-shm", ".recovery.lock")}
    if str(path) in reserved or str(path) + ".lock" in reserved:
        raise TrustError("startup state must be separate from the database and its sidecars")
    # Keep the original path so locked_state can reject a final symlink.
    return str(policy.state_path)


def _status(writer: "Writer", log_id: str, policy: StartupPolicy,
            state: StateTransaction) -> int:
    if writer._trust_pins is None or log_id not in writer._trust_pins:
        raise TrustError("verified startup requires independent trust pins")
    pins = writer._trust_pins[log_id]
    if type(pins.minimum_status_serial) is not int \
            or not 1 <= pins.minimum_status_serial <= SAFE_INT_MAX:
        raise TrustError("status serial minimum must be a positive safe integer")
    previous = state.previous
    minimum = max(pins.minimum_status_serial, previous.status_serial if previous else 1)
    report = verify(writer.manifest_envelope(log_id), (), replace(
        pins, minimum_status_serial=minimum), status_envelopes=policy.status_envelopes,
        retained_revoked=previous.revoked if previous else False,
        max_chain_steps=policy.max_chain_steps)
    serial = max(report.observed_status_serial, previous.status_serial if previous else 0)
    if report.observed_status_serial or report.trust_status is TrustStatus.REVOKED:
        state.save(serial, None, revoked=report.trust_status is TrustStatus.REVOKED)
    if report.result is not Result.PASS or report.trust_status is not TrustStatus.OK:
        raise TrustError("startup requires active signed status at the retained serial; "
                         + ", ".join(report.diagnostic_codes))
    return serial


def authorize(writer: "Writer", policy: StartupPolicy) -> LatestView:
    """Keep writes held until status, witness and external persistence succeed."""
    policy = policy.copied()
    rows = writer._db.connection.execute("SELECT log_id FROM manifests").fetchall()
    if len(rows) != 1:
        raise TrustError("verified startup requires exactly one provisioned log")
    log_id = rows[0][0]
    context = writer._manifest_context(writer.manifest_envelope(log_id))
    if writer._signing_key()[2] != context.body["log_key_id"]:
        raise TrustError("writer key does not match the provisioned log key")
    # This commit precedes missing/invalid external-state or status failures.
    hold_writer(writer, log_id)
    path = _state_path(writer, policy)
    with locked_state(path, context.digest, initialize=policy.initialize_state) as state:
        serial = _status(writer, log_id, policy, state)
        previous = state.previous
        pending = writer.pending_checkpoint(log_id)
        count = writer._db.connection.execute(
            "SELECT count FROM heads WHERE log_id=?", (log_id,)).fetchone()[0]
        if count == 0 and pending is None and not writer._db.connection.execute(
                "SELECT 1 FROM checkpoints WHERE log_id=?", (log_id,)).fetchone():
            writer._bootstrapping = True
            try:
                writer.create_checkpoint(log_id)
            finally:
                writer._bootstrapping = False
            pending = writer.pending_checkpoint(log_id)
        # An empty first checkpoint is a resumable bootstrap, not permission
        # to treat an unsigned NO_CHECKPOINT reply as fresh accepted evidence.
        if count == 0 and pending is not None:
            body = cast(JsonObject, pending[0]["body"])
            if body["index"] == 0 and body["count"] == 0:
                writer.submit_pending(log_id, policy.witness_url, policy.token,
                                      timeout=policy.timeout)

        def retain(view: LatestView) -> None:
            state.save(serial, (cast(int, view.body["checkpoint_index"]),
                                cast(str, view.body["checkpoint_hash"])))

        view = reconcile_witness(
            writer, log_id, policy.witness_url, policy.token,
            timeout=policy.timeout, max_chain_steps=policy.max_chain_steps,
            retained_checkpoint=previous.checkpoint if previous else None,
            before_resume=retain)
    writer._startup_policy = replace(policy, initialize_state=False)
    writer._startup_log_id = log_id
    writer._startup_serial = serial
    return view


@contextmanager
def write_authorization(writer: "Writer", log_id: str) -> Iterator[None]:
    if writer._startup_failed:
        raise TrustError("failed state persistence requires verified startup again")
    policy = writer._startup_policy
    if policy is None:
        yield  # explicitly local-only writer, or keyless evidence operation
        return
    if log_id != writer._startup_log_id:
        raise TrustError("verified writer is scoped to its authorized log")
    if writer._active_state is not None:
        yield  # nested receipt storage during submission shares the outer lock
        return
    manifest = writer.manifest_envelope(log_id)
    with locked_state(_state_path(writer, policy), cast(str, manifest["manifest_hash"])) as state:
        previous = state.previous
        if previous is None or previous.revoked:
            raise TrustError("retained authority status is revoked or missing")
        if previous.status_serial > writer._startup_serial:
            raise TrustError("newer authority status requires verified startup again")
        if previous.checkpoint is None:
            raise TrustError("verified startup checkpoint is missing")
        row = writer._db.connection.execute(
            "SELECT checkpoint_hash FROM checkpoints WHERE log_id=? AND idx=? AND state='accepted'",
            (log_id, previous.checkpoint[0])).fetchone()
        if row != (previous.checkpoint[1],):
            raise TrustError("local journal does not contain the retained startup checkpoint")
        writer._active_state = state
        try:
            yield
        finally:
            writer._active_state = None


def authorized[**P, T](method: Callable[Concatenate["Writer", str, P], T]
               ) -> Callable[Concatenate["Writer", str, P], T]:
    @wraps(method)
    def wrapped(writer: "Writer", log_id: str, *args: P.args, **kwargs: P.kwargs) -> T:
        with write_authorization(writer, log_id):
            return method(writer, log_id, *args, **kwargs)
    return cast(Callable[Concatenate["Writer", str, P], T], wrapped)


def reserve_database(path: str | Path) -> None:
    if any(os.path.lexists(str(path) + suffix) for suffix in ("", "-wal", "-shm")):
        raise CasfError("initialization requires a new database")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
