"""R02/R09: retained state replacement, revocation and lock release on SIGKILL."""

import os
import stat

import pytest

from casf.errors import CasfError
from casf.trust.state import SavedState, locked_state
from tests.process.support import finish, kill, pause, receive, worker

MANIFEST = "ab" * 32
OTHER = "cd" * 32
OLD = (0, "01" * 32)
NEW = (1, "02" * 32)


def _seed(path):
    with locked_state(str(path), MANIFEST, initialize=True) as state:
        state.save(1, OLD)
    with locked_state(str(path), OTHER, initialize=True) as state:
        state.save(7, OLD, revoked=True)


def _crash_save(path, stage, pipe):
    import casf.trust.state as module

    replace, fsync = os.replace, os.fsync

    def replace_at_boundary(*args, **kwargs):
        if stage == "before_replace":
            pause(pipe, stage)
        replace(*args, **kwargs)
        if stage == "after_replace":
            pause(pipe, stage)

    def fsync_at_boundary(fd):
        fsync(fd)
        if stage == "after_directory_fsync" and stat.S_ISDIR(os.fstat(fd).st_mode):
            pause(pipe, stage)

    module.os.replace = replace_at_boundary
    module.os.fsync = fsync_at_boundary
    with locked_state(str(path), MANIFEST) as state:
        state.save(2, NEW, revoked=True)
    raise AssertionError("state save missed crash barrier")


@pytest.mark.parametrize("stage", ["before_replace", "after_replace", "after_directory_fsync"])
def test_killed_state_save_preserves_complete_history_and_other_manifests(tmp_path, stage):
    path = tmp_path / "state.json"
    _seed(path)
    old_bytes = path.read_bytes()
    lock_inode = path.with_suffix(".json.lock").stat().st_ino
    with worker(_crash_save, path, stage) as (process, pipe):
        receive(pipe, stage)
        kill(process)
    with locked_state(str(path), MANIFEST) as state:
        if stage == "before_replace":
            assert path.read_bytes() == old_bytes
            assert state.previous == SavedState(1, OLD)
        else:
            assert state.previous == SavedState(2, NEW, revoked=True)
        assert state.entries[OTHER] == SavedState(7, OLD, revoked=True)
        # Retry completes any interrupted replacement; newer active status
        # cannot clear terminal revocation or replace retained checkpoint history.
        state.save(2, NEW, revoked=True)
        state.save(3, NEW, revoked=False)
        assert state.previous == SavedState(3, NEW, revoked=True)
        with pytest.raises(CasfError, match="status serial"):
            state.save(1, NEW)
        with pytest.raises(CasfError, match="retained history"):
            state.save(3, OLD)
    with locked_state(str(path), OTHER) as state:
        assert state.previous == SavedState(7, OLD, revoked=True)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.with_suffix(".json.lock").stat().st_ino == lock_inode


def _waiting_save(path, pipe):
    import fcntl

    flock = fcntl.flock

    def announce(fd, operation):
        pipe.send(("attempting", None))
        return flock(fd, operation)

    fcntl.flock = announce
    with locked_state(str(path), MANIFEST) as state:
        previous = state.previous
        state.save(3, NEW)
    pipe.send(("result", previous))


def test_killed_state_lock_holder_releases_waiting_process(tmp_path):
    path = tmp_path / "state.json"
    _seed(path)
    inode = path.with_suffix(".json.lock").stat().st_ino
    with worker(_crash_save, path, "after_replace") as (first, first_pipe):
        receive(first_pipe, "after_replace")
        with worker(_waiting_save, path) as (second, second_pipe):
            receive(second_pipe, "attempting")
            kill(first)
            assert receive(second_pipe, "result") == SavedState(2, NEW, revoked=True)
            finish(second)
    with locked_state(str(path), MANIFEST) as state:
        assert state.previous == SavedState(3, NEW, revoked=True)
        assert state.entries[OTHER] == SavedState(7, OLD, revoked=True)
    assert path.with_suffix(".json.lock").stat().st_ino == inode
