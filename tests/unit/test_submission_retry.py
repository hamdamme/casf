"""R05/R10: retry only transient transport outcomes, retaining exact bytes."""

import pytest

from casf.errors import CasfError, InconclusiveError
from tests.unit.test_writer import LOG_ID, _append, _writer


@pytest.mark.parametrize("status", [429, 503, 400, 401, 403, 409, 413])
def test_submission_classifies_http_failure_and_counts_attempt(tmp_path, monkeypatch, status):
    writer = _writer(tmp_path / "writer.db")
    try:
        _append(writer, 1)
        writer.create_checkpoint(LOG_ID)
        before = writer.pending_checkpoint(LOG_ID)

        def response(*args, **kwargs):
            assert not writer._db.connection.in_transaction
            return status, b'{"code":"untrusted diagnostic","message":"secret","retryable":true}'

        monkeypatch.setattr("casf.writer.http_request", response)
        with pytest.raises(CasfError) as error:
            writer.submit_pending(LOG_ID, "http://127.0.0.1:1", "test-token")
        assert isinstance(error.value, InconclusiveError) == (status in (429, 503))
        assert "secret" not in str(error.value)
        assert "untrusted diagnostic" not in str(error.value)
        assert writer.pending_checkpoint(LOG_ID) == before
        assert writer._db.connection.execute("SELECT attempts FROM outbox").fetchone() == (1,)
    finally:
        writer.close()


def test_plain_service_unavailable_is_retryable(tmp_path, monkeypatch):
    writer = _writer(tmp_path / "writer.db")
    try:
        writer.create_checkpoint(LOG_ID)
        monkeypatch.setattr("casf.writer.http_request", lambda *a, **kw: (503, b"Unavailable"))
        with pytest.raises(InconclusiveError):
            writer.submit_pending(LOG_ID, "http://127.0.0.1:1", "test-token")
    finally:
        writer.close()


def test_transport_value_error_cannot_expose_credentials(tmp_path, monkeypatch):
    writer = _writer(tmp_path / "writer.db")
    try:
        writer.create_checkpoint(LOG_ID)

        def invalid(*args, **kwargs):
            raise ValueError("invalid header containing synthetic-secret-token")

        monkeypatch.setattr("casf.writer.http_request", invalid)
        with pytest.raises(CasfError, match="invalid witness request configuration") as error:
            writer.submit_pending(LOG_ID, "http://127.0.0.1:1", "synthetic-secret-token")
        assert "synthetic-secret-token" not in str(error.value)
        assert writer.pending_checkpoint(LOG_ID) is not None
    finally:
        writer.close()
