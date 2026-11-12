"""R04/R05/R09: generated durable-outbox and backup operation sequences.

This exercises local storage APIs and the real witness state machine. It does
not model network transport, verified startup, power loss or independent admins.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.errors import CasfError
from casf.verifier import Result
from casf.witness import Witness
from casf.writer import Writer
from tests.unit.test_checkpoint import _pending_records, _witness
from tests.unit.test_writer import AUTH_PUB, LOG, LOG_ID, WIT, _append, _verify_db, _writer
from tests.unit.test_writer_trust import _pins


class RecoverySequences(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.directory = TemporaryDirectory(prefix='casf-generated-recovery-')
        self.root = Path(self.directory.name)
        self.writer = _writer(self.root / 'writer.db', trust_pins={LOG_ID: _pins()})
        self.witness = _witness(self.root)
        self.records = []
        self.pending_bytes = None
        self.accepted_receipt = None
        self.accepted_count = 0
        self.last_accepted_checkpoint = None
        self.backup_number = 0

    @rule()
    def append(self):
        record = _append(self.writer, len(self.records) + 1)
        self.records.append(canonicalize(record))

    @precondition(lambda self: bool(self.records))
    @rule()
    def retry_event(self):
        assert canonicalize(_append(self.writer, len(self.records))) == self.records[-1]

    @precondition(lambda self: self.pending_bytes is None)
    @rule()
    def checkpoint(self):
        self.pending_bytes = canonicalize(self.writer.create_checkpoint(LOG_ID))
        self.accepted_receipt = None

    @precondition(lambda self: self.pending_bytes is not None)
    @rule()
    def accept_without_recording_reply(self):
        pending = self.writer.pending_checkpoint(LOG_ID)
        receipt = self.witness.submit(LOG_ID, pending[0], _pending_records(self.writer, pending))
        if self.accepted_receipt is not None:
            assert canonicalize(receipt) == canonicalize(self.accepted_receipt)
        self.accepted_receipt = receipt
        self.accepted_count = pending[0]['body']['count']
        self.last_accepted_checkpoint = pending[0]
        assert canonicalize(self.writer.pending_checkpoint(LOG_ID)[0]) == self.pending_bytes

    @precondition(lambda self: self.accepted_receipt is not None)
    @rule()
    def reject_forged_receipt(self):
        forged = dict(self.accepted_receipt)
        forged['signature'] = crypto.b64url_encode(bytes(64))
        with pytest.raises(CasfError):
            self.writer.record_receipt(LOG_ID, forged)
        assert canonicalize(self.writer.pending_checkpoint(LOG_ID)[0]) == self.pending_bytes

    @precondition(lambda self: self.accepted_receipt is not None)
    @rule()
    def recover_accepted_reply(self):
        checkpoint = self.writer.pending_checkpoint(LOG_ID)[0]
        recovered_checkpoint, receipt = self.witness.receipt(checkpoint['checkpoint_hash'])
        assert canonicalize(recovered_checkpoint) == self.pending_bytes
        assert canonicalize(receipt) == canonicalize(self.accepted_receipt)
        self.writer.record_receipt(LOG_ID, receipt)
        self.pending_bytes = None
        self.accepted_receipt = None

    @rule()
    def restart_writer(self):
        self.writer.close()
        self.writer = Writer(self.root / 'writer.db', LOG,
                             trust_pins={LOG_ID: _pins()}, local_only=True)

    @rule()
    def restart_witness(self):
        self.witness.close()
        self.witness = Witness(self.root / 'wit.db', WIT,
                               authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})

    @rule()
    def inspect_backup_without_authorizing_writes(self):
        # A locally intact backup is not permission to resume against a witness.
        self.backup_number += 1
        destination = self.root / f'backup-{self.backup_number}.db'
        self.writer.backup(destination)
        reader = Writer(destination, trust_pins={LOG_ID: _pins()})
        try:
            assert [canonicalize(r) for r in reader.records(LOG_ID)] == self.records
            pending = reader.pending_checkpoint(LOG_ID)
            assert (canonicalize(pending[0]) if pending else None) == self.pending_bytes
            assert _verify_db(reader).result is Result.PASS
        finally:
            reader.close()

    @invariant()
    def committed_history_and_outbox_match_model(self):
        assert [canonicalize(r) for r in self.writer.records(LOG_ID)] == self.records
        pending = self.writer.pending_checkpoint(LOG_ID)
        assert (canonicalize(pending[0]) if pending else None) == self.pending_bytes
        assert self.accepted_count <= len(self.records)
        if self.last_accepted_checkpoint is not None:
            latest = self.witness.latest(LOG_ID, bytes(32))
            assert latest['body']['count'] == self.accepted_count
            assert latest['body']['checkpoint_hash'] == self.last_accepted_checkpoint['checkpoint_hash']
        assert _verify_db(self.writer).result is Result.PASS

    def teardown(self):
        self.writer.close()
        self.witness.close()
        self.directory.cleanup()


TestRecoverySequences = RecoverySequences.TestCase
TestRecoverySequences.settings = settings(max_examples=40, stateful_step_count=30, deadline=None)
