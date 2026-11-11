"""Spawned workers stop at explicit barriers until killed by the parent."""

import multiprocessing
import signal
from contextlib import contextmanager

MP = multiprocessing.get_context("spawn")
TIMEOUT = 20


@contextmanager
def worker(target, *args):
    parent, child = MP.Pipe()
    process = MP.Process(target=target, args=(*args, child))
    try:
        process.start()
        child.close()
        yield process, parent
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.kill()
            process.join(TIMEOUT)
            assert not process.is_alive(), "worker did not exit"
            process.close()
        parent.close()
        child.close()


def receive(pipe, stage):
    assert pipe.poll(TIMEOUT), f"worker did not reach {stage}"
    actual, snapshot = pipe.recv()
    assert actual == stage
    return snapshot


def pause(pipe, stage, snapshot=None):
    pipe.send((stage, snapshot))
    # No exception handler or graceful shutdown runs after the parent's SIGKILL.
    pipe.recv()
    raise AssertionError("crash barrier must be terminated, not released")


def kill(process):
    process.kill()
    process.join(TIMEOUT)
    assert process.exitcode == -signal.SIGKILL


def finish(process):
    process.join(TIMEOUT)
    assert process.exitcode == 0


class CommitBarrier:
    """Test-only connection proxy; keep real SQLite transaction behavior."""

    def __init__(self, connection, pipe, stage, snapshot, predicate=lambda con: True):
        self.connection = connection
        self.pipe = pipe
        self.stage = stage
        self.snapshot = snapshot
        self.predicate = predicate

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        selected = self.predicate(self.connection)
        if selected and self.stage == "before_commit":
            pause(self.pipe, self.stage, self.snapshot(self.connection))
        self.connection.commit()
        if selected and self.stage == "after_commit":
            pause(self.pipe, self.stage, self.snapshot(self.connection))


class BeginSignal:
    """Announce an attempted write transaction without replacing SQLite locks."""

    def __init__(self, connection, pipe):
        self.connection = connection
        self.pipe = pipe

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, sql, *args, **kwargs):
        if sql == "BEGIN IMMEDIATE":
            self.pipe.send(("attempting", None))
        return self.connection.execute(sql, *args, **kwargs)
