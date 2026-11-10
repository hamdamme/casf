"""R04/R09: persist the evidence that was validated, despite caller mutation."""

import pytest

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.errors import SchemaError
from casf.writer import Writer
from tests.unit.test_writer import LOG, LOG_ID, _append, _manifest_envelope, _writer


def test_create_log_snapshots_manifest_before_validation_and_storage(tmp_path, monkeypatch):
    manifest = _manifest_envelope()
    expected = canonicalize(manifest)
    writer = Writer(tmp_path / 'writer.db', LOG, local_only=True)
    original = writer._manifest_context

    def mutate(value):
        result = original(value)
        manifest['signature'] = 'A' * 86
        return result

    monkeypatch.setattr(writer, '_manifest_context', mutate)
    try:
        writer.create_log(manifest)
        assert canonicalize(writer.manifest_envelope(LOG_ID)) == expected
    finally:
        writer.close()


def test_receipt_snapshots_validated_signature_before_storage(tmp_path, monkeypatch):
    from casf.witness import Witness
    from tests.status import register_active
    from tests.unit.test_writer import AUTH, AUTH_PUB, WIT

    writer = _writer(tmp_path / 'writer.db')
    witness = Witness(tmp_path / 'witness.db', WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    try:
        record = _append(writer)
        checkpoint = writer.create_checkpoint(LOG_ID)
        receipt = witness.submit(LOG_ID, checkpoint, [record])
        expected = canonicalize(receipt)
        original = crypto.verify_receipt

        def mutate(*args):
            original(*args)
            receipt['signature'] = 'A' * 86

        monkeypatch.setattr(crypto, 'verify_receipt', mutate)
        writer.record_receipt(LOG_ID, receipt)
        stored = writer._db.connection.execute('SELECT envelope FROM receipts').fetchone()[0]
        assert stored == expected
        assert writer.pending_checkpoint(LOG_ID) is None
    finally:
        writer.close()
        witness.close()


@pytest.mark.parametrize('final', [None, 0, 1, 'false', [], {}])
def test_checkpoint_rejects_nonboolean_final_before_a_transaction(tmp_path, final):
    writer = _writer(tmp_path / 'writer.db')
    statements = []
    writer._db.connection.set_trace_callback(statements.append)
    try:
        with pytest.raises(SchemaError):
            writer.create_checkpoint(LOG_ID, final=final)
        assert not any(sql.startswith('BEGIN') for sql in statements)
        assert writer.pending_checkpoint(LOG_ID) is None
    finally:
        writer.close()
