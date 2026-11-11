"""Retained status cannot be rolled back by stale readers or invalid input."""

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.lifecycle import StatusBook
from tests.unit.test_lifecycle import _status
from tests.unit.test_writer import AUTH, AUTH_PUB

HASH = "ab" * 32


def test_stale_instance_cannot_overwrite_newer_status(tmp_path):
    path = tmp_path / "status.json"
    first, stale = StatusBook(path), StatusBook(path)
    assert first.observe(_status(3, mh=HASH), AUTH_PUB)
    assert not stale.observe(_status(2, mh=HASH), AUTH_PUB)
    assert StatusBook(path).observed_serial(HASH) == 3


def test_stale_instance_preserves_revocation(tmp_path):
    path = tmp_path / "status.json"
    first, stale = StatusBook(path), StatusBook(path)
    assert first.observe(_status(1, mh=HASH, status="revoked"), AUTH_PUB)
    assert not stale.observe(_status(2, mh=HASH), AUTH_PUB)


def test_out_of_order_revocation_is_terminal(tmp_path):
    book = StatusBook(tmp_path / "status.json")
    assert book.observe(_status(3, mh=HASH), AUTH_PUB)
    assert book.observe(_status(2, mh=HASH, status="revoked"), AUTH_PUB)
    assert book.observed_serial(HASH) == 3
    assert not book.observe(_status(4, mh=HASH), AUTH_PUB)


@pytest.mark.parametrize("field,value", [("status", "unknown"), ("issuer_id", "00" * 32)])
def test_signed_invalid_status_is_not_persisted(tmp_path, field, value):
    path = tmp_path / "status.json"
    book = StatusBook(path)
    statement = _status(1, mh=HASH)
    statement["body"][field] = value
    statement["signature"] = crypto.sign_status(AUTH, statement["body"])
    with pytest.raises(CasfError):
        book.observe(statement, AUTH_PUB)
    assert not path.exists()


def test_rejects_symlink_without_overwriting_target(tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("{}")
    path = tmp_path / "status.json"
    path.symlink_to(victim)
    with pytest.raises(CasfError):
        StatusBook(path)
    assert victim.read_text() == "{}"
