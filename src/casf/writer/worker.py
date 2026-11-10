"""Foreground checkpoint scheduling with durable retries (SPEC sections 12–14)."""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import TYPE_CHECKING

from casf.canonical.limits import MAX_CHECKPOINT_BATCH, SAFE_INT_MAX
from casf.errors import CasfError, InconclusiveError, SchemaError, TrustError
from casf.types import JsonObject
from casf.writer.recovery import recovery_lock
from casf.writer.startup import write_authorization

if TYPE_CHECKING:
    from casf.writer import Writer


def _duration(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or not 0.001 <= value <= 86400:
        raise SchemaError("worker durations must be between 0.001 and 86400 seconds")
    return float(value)


def _deadline(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or not 0 <= value <= 1e12:
        raise SchemaError("worker clock or stored deadline is invalid")
    return float(value)


@dataclass(frozen=True)
class WorkerResult:
    state: str
    committed: int
    witnessed: int
    backlog: int
    pending_checkpoint_hash: str | None
    attempts: int
    next_action_at_ms: int | None

    def as_json(self) -> JsonObject:
        return {"state": self.state, "committed": self.committed,
                "witnessed": self.witnessed, "backlog": self.backlog,
                "pending_checkpoint_hash": self.pending_checkpoint_hash,
                "attempts": self.attempts, "next_action_at_ms": self.next_action_at_ms}


class CheckpointWorker:
    """Use one verified writer connection in the thread executing tick or run."""

    def __init__(self, writer: "Writer", log_id: str, *, interval_seconds: float = 60,
                 retry_initial_seconds: float = 1, retry_max_seconds: float = 60,
                 clock: Callable[[], float] = time.time) -> None:
        if writer._startup_policy is None or writer._startup_log_id != log_id:
            raise TrustError("checkpoint worker requires a verified writer for this log")
        self.writer, self.log_id = writer, log_id
        self.interval = _duration(interval_seconds)
        self.retry_initial = _duration(retry_initial_seconds)
        self.retry_max = _duration(retry_max_seconds)
        if self.retry_initial > self.retry_max:
            raise SchemaError("initial retry delay exceeds the maximum")
        self.clock = clock

    def _read(self) -> tuple[int, int, int, str, str | None, int, float]:
        row = self.writer._db.connection.execute(
            "SELECT h.count, h.sealed, "
            "COALESCE((SELECT count FROM checkpoints WHERE log_id=h.log_id "
            "AND state='accepted' ORDER BY idx DESC LIMIT 1), 0), "
            "(SELECT checkpoint_hash FROM checkpoints WHERE log_id=h.log_id "
            "AND state='accepted' ORDER BY idx DESC LIMIT 1), "
            "o.checkpoint_hash, COALESCE(o.attempts, 0), COALESCE(o.next_attempt_at, 0) "
            "FROM heads h LEFT JOIN outbox o ON o.log_id=h.log_id WHERE h.log_id=?",
            (self.log_id,)).fetchone()
        if row is None or not isinstance(row[3], str):
            raise CasfError("worker requires an accepted startup checkpoint")
        if type(row[5]) is not int or not 0 <= row[5] <= SAFE_INT_MAX:
            raise SchemaError("stored retry count is invalid")
        return row[0], row[1], row[2], row[3], row[4], row[5], _deadline(row[6])

    def _report(self, state: str, due: float | None = None) -> WorkerResult:
        count, _, witnessed, _, pending, attempts, _ = self._read()
        return WorkerResult(state, count, witnessed, count - witnessed, pending,
                            attempts, None if due is None else math.ceil(due * 1000))

    def _schedule(self, digest: str, due: float) -> None:
        con = self.writer._db.connection
        with con:
            con.execute(
                "INSERT INTO checkpoint_schedule VALUES (?, ?, ?) ON CONFLICT(log_id) "
                "DO UPDATE SET checkpoint_hash=excluded.checkpoint_hash, "
                "next_checkpoint_at=excluded.next_checkpoint_at",
                (self.log_id, digest, due))

    def _retry_at(self, digest: str, due: float) -> None:
        con = self.writer._db.connection
        with con:
            changed = con.execute(
                "UPDATE outbox SET next_attempt_at=? WHERE log_id=? AND checkpoint_hash=?",
                (due, self.log_id, digest)).rowcount
            if changed != 1:
                raise CasfError("pending checkpoint changed before retry scheduling")

    def tick(self) -> WorkerResult:
        """Perform at most one bounded submission; permanent failures propagate."""
        from casf.writer import ReconciliationRequiredError, RestoreBehindWitnessError

        writer = self.writer
        policy = writer._startup_policy
        assert policy is not None
        # Match startup lock ordering; no SQLite transaction spans network work.
        with write_authorization(writer, self.log_id), recovery_lock(writer, policy.timeout):
            now = _deadline(self.clock())
            count, sealed, witnessed, digest, pending, attempts, retry_at = self._read()
            if sealed == 1:
                raise RestoreBehindWitnessError("RESTORE_BEHIND_WITNESS: worker cannot resume")
            if sealed == 3:
                raise ReconciliationRequiredError("RECONCILIATION_REQUIRED: worker cannot resume")
            if pending is None:
                if sealed:
                    return self._report("sealed")
                row = writer._db.connection.execute(
                    "SELECT checkpoint_hash, next_checkpoint_at FROM checkpoint_schedule "
                    "WHERE log_id=?", (self.log_id,)).fetchone()
                due = (min(_deadline(row[1]), now + self.interval)
                       if row is not None and row[0] == digest else now)
                if row is None or row[0] != digest or row[1] != due:
                    self._schedule(digest, due)
                if count - witnessed < MAX_CHECKPOINT_BATCH and now < due:
                    return self._report("idle", due)
                writer.create_checkpoint(self.log_id)
                _, _, _, _, pending, attempts, retry_at = self._read()
            assert pending is not None
            due = min(retry_at, now + self.retry_max)
            if now < due:
                if due != retry_at:
                    self._retry_at(pending, due)
                return self._report("waiting", due)
            delay = min(self.retry_max, self.retry_initial * 2 ** min(attempts, 32))
            # Persist a deadline before the request so a crash does not erase it.
            self._retry_at(pending, now + delay)
            try:
                writer.submit_pending(self.log_id, policy.witness_url, policy.token,
                                      timeout=policy.timeout)
            except InconclusiveError:
                due = _deadline(self.clock()) + delay
                self._retry_at(pending, due)
                return self._report("retry", due)
            count, sealed, witnessed, digest, _, _, _ = self._read()
            due = _deadline(self.clock()) + (0 if count > witnessed else self.interval)
            self._schedule(digest, due)
            return self._report("sealed" if sealed else "witnessed", None if sealed else due)

    def run(self, stop: Event, *, poll_interval: float = 1,
            on_result: Callable[[WorkerResult], None] | None = None) -> WorkerResult | None:
        """Run in the calling thread; stop waits are interruptible."""
        interval = _duration(poll_interval)
        previous = None
        while not stop.is_set():
            result = self.tick()
            if on_result is not None and result != previous:
                on_result(result)
            previous = result
            if result.state == "sealed":
                break
            if result.state == "witnessed" and result.backlog:
                continue
            stop.wait(interval)
        return previous
