"""Durable verifier observations survive errors and serialize concurrent updates."""

import json
import multiprocessing
import os
import stat

import pytest

from casf.errors import CasfError
from casf.trust.state import MAX_STATE_BYTES, locked_state

MANIFEST = "a" * 64
CHECKPOINT = "b" * 64


def seed(path):
    with locked_state(str(path), MANIFEST, initialize=True) as transaction:
        transaction.save(1, (0, CHECKPOINT))


def test_first_use_is_explicit_and_cannot_reset(tmp_path):
    path = tmp_path / "state.json"
    with pytest.raises(CasfError, match="missing"), locked_state(str(path), MANIFEST):
        pytest.fail("missing state was accepted")
    assert not path.exists()
    with locked_state(str(path), MANIFEST, initialize=True):
        pass  # failed verification does not save an observation
    assert not path.exists()
    seed(path)
    before = path.read_bytes()
    with (
        pytest.raises(CasfError, match="already exists"),
        locked_state(str(path), MANIFEST, initialize=True),
    ):
        pytest.fail("existing state was reset")
    assert path.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_state_preserves_other_manifests_and_checkpoint(tmp_path):
    path = tmp_path / "state.json"
    seed(path)
    with locked_state(str(path), "c" * 64, initialize=True) as transaction:
        transaction.save(4, None)
    with locked_state(str(path), MANIFEST) as transaction:
        assert transaction.previous.status_serial == 1
        transaction.save(2, None)
    with locked_state(str(path), MANIFEST) as transaction:
        assert transaction.previous.checkpoint == (0, CHECKPOINT)
        assert transaction.previous.status_serial == 2
    with locked_state(str(path), "c" * 64) as transaction:
        assert transaction.previous.status_serial == 4


@pytest.mark.parametrize("serial,checkpoint", [(0, None), (1, (0, "c" * 64)), (1, (-1, CHECKPOINT))])
def test_save_rejects_regression(tmp_path, serial, checkpoint):
    path = tmp_path / "state.json"
    seed(path)
    before = path.read_bytes()
    with locked_state(str(path), MANIFEST) as transaction, pytest.raises(CasfError):
        transaction.save(serial, checkpoint)
    assert path.read_bytes() == before


@pytest.mark.parametrize("raw", [b"", b"broken", b'{"version":1,"version":1,"manifests":{}}',
                                 b'{"version":true,"manifests":{}}', b"x" * (MAX_STATE_BYTES + 1)],
                         ids=["empty", "invalid_json", "duplicate_version",
                              "boolean_version", "oversized"])
def test_bad_state_never_reinitialized(tmp_path, raw):
    path = tmp_path / "state.json"
    path.write_bytes(raw)
    path.chmod(0o600)
    with pytest.raises(CasfError), locked_state(str(path), MANIFEST, initialize=True):
        pytest.fail("damaged state was reset")
    assert path.read_bytes() == raw


@pytest.mark.parametrize("target", ["state", "lock"])
def test_symlinks_rejected(tmp_path, target):
    path = tmp_path / "state.json"
    victim = tmp_path / "victim"
    victim.write_text("unchanged")
    victim.chmod(0o600)
    link = path if target == "state" else path.with_name(path.name + ".lock")
    link.symlink_to(victim)
    with pytest.raises(OSError), locked_state(str(path), MANIFEST, initialize=True):
        pytest.fail("symlink followed")
    assert victim.read_text() == "unchanged"


def test_shared_permissions_and_hard_links_rejected(tmp_path):
    path = tmp_path / "state.json"
    seed(path)
    path.chmod(0o644)
    with pytest.raises(CasfError, match="owner only"), locked_state(str(path), MANIFEST):
        pass
    path.chmod(0o600)
    os.link(path, tmp_path / "other")
    with pytest.raises(CasfError, match="hard links"), locked_state(str(path), MANIFEST):
        pass


def test_atomic_replace_failure_preserves_previous_state(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    seed(path)
    before = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(os, "replace", fail)
    with locked_state(str(path), MANIFEST) as transaction, pytest.raises(OSError):
        transaction.save(2, (1, "c" * 64))
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".casf-state-*"))


def _first_worker(path, entered, release):
    with locked_state(path, MANIFEST) as transaction:
        entered.set()
        if not release.wait(10):
            raise RuntimeError("test did not release lock")
        transaction.save(2, (1, "c" * 64))


def _second_worker(path, attempting, acquired, observed):
    attempting.set()
    with locked_state(path, MANIFEST) as transaction:
        observed.value = transaction.previous.status_serial
        acquired.set()
        transaction.save(3, (2, "d" * 64))


def test_concurrent_processes_read_latest_state_under_lock(tmp_path):
    path = tmp_path / "state.json"
    seed(path)
    context = multiprocessing.get_context("spawn")
    entered, release, attempting, acquired = [context.Event() for _ in range(4)]
    observed = context.Value("i", 0)
    first = context.Process(target=_first_worker, args=(str(path), entered, release))
    second = context.Process(target=_second_worker,
                             args=(str(path), attempting, acquired, observed))
    first.start()
    try:
        assert entered.wait(10)
        second.start()
        assert attempting.wait(10)
        assert not acquired.wait(0.2)
        release.set()
        first.join(10)
        second.join(10)
        assert first.exitcode == second.exitcode == 0
        assert observed.value == 2
        state = json.loads(path.read_text())["manifests"][MANIFEST]
        assert state["status_serial"] == 3
        assert state["checkpoint"]["index"] == 2
    finally:
        release.set()
        for process in [first, second]:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(10)
