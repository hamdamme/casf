# ruff: noqa: F811
"""Synthetic application entry preserves verified startup and retry semantics."""

import json

import pytest

from casf.canonical.jcs import canonicalize
from casf.writer import Writer
from examples.transactions import main
from tests.unit.test_cli_verified_startup import initialize
from tests.unit.test_cli_verified_startup import setup as verified_setup  # noqa: F401
from tests.unit.test_verified_startup import statement
from tests.unit.test_writer import LOG_ID

EVENT = '123e4567-e89b-42d3-a456-426614174001'
SECOND = '123e4567-e89b-42d3-a456-426614174002'
TRANSACTION = '123e4567-e89b-42d3-a456-426614174099'


def arguments(common, **changes):
    fields = {'event-id': EVENT, 'transaction-id': TRANSACTION, 'event': 'created',
              'amount-minor': '1250', 'currency': 'USD'}
    fields.update(changes)
    return [*common, '--synthetic', *[part for key, value in fields.items()
                                    for part in ('--' + key, value)]]


def test_create_retry_and_refund_are_witnessed_without_editing_history(verified_setup, tmp_path, capsys):
    common, *_ = verified_setup
    assert initialize(verified_setup) == 0
    capsys.readouterr()
    assert main(arguments(common)) == 0
    results = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert results[-1]['witnessed'] == 1 and results[-1]['backlog'] == 0
    assert main(arguments(common)) == 0
    assert main(arguments(common, **{'event-id': SECOND, 'event': 'refunded',
                                    'related-event-id': EVENT})) == 0
    reader = Writer(tmp_path / 'writer.db')
    try:
        records = list(reader.records(LOG_ID))
        assert len(records) == 2
        assert records[0]['body']['event_type'] == 'transaction-created'
        assert records[1]['body']['event_type'] == 'transaction-refunded'
        assert records[1]['body']['payload']['related_event_id'] == EVENT
        assert records[0]['body']['payload']['amount_minor'] == 1250
        assert records[0]['body']['payload']['synthetic'] is True
    finally:
        reader.close()


@pytest.mark.parametrize('change', [
    {'amount-minor': '1.25'}, {'amount-minor': '-1'}, {'amount-minor': '9007199254740992'},
    {'currency': 'usd'}, {'event-id': 'invalid'}, {'event': 'refunded'},
    {'related-event-id': SECOND},
    {'event': 'corrected', 'related-event-id': EVENT},
])
def test_invalid_input_does_not_open_database(tmp_path, change):
    common = [part for name in ('db', 'key', 'trust', 'status-file', 'state')
              for part in ('--' + name, str(tmp_path / name))]
    with pytest.raises(SystemExit) as exc:
        main(arguments(common, **change))
    assert exc.value.code == 2
    assert not (tmp_path / 'db').exists()


def test_changed_retry_and_revoked_trust_do_not_append(verified_setup, tmp_path, capsys):
    common, _, status, *_ = verified_setup
    assert initialize(verified_setup) == 0
    assert main(arguments(common)) == 0
    assert main(arguments(common, **{'amount-minor': '999'})) != 0
    status.write_bytes(canonicalize(statement(2, 'revoked')))
    assert main(arguments(common, **{'event-id': SECOND})) == 3
    reader = Writer(tmp_path / 'writer.db')
    try:
        assert len(list(reader.records(LOG_ID))) == 1
    finally:
        reader.close()


@pytest.mark.parametrize('stage', ['append', 'checkpoint', 'witness'])
def test_stage_failure_stops_and_preserves_exit_category(monkeypatch, tmp_path, stage):
    calls = []

    def command(args):
        calls.append(args[0])
        return 4 if args[0] == stage else 0

    monkeypatch.setattr('examples.transactions.casf_main', command)
    common = [part for name in ('db', 'key', 'trust', 'status-file', 'state')
              for part in ('--' + name, str(tmp_path / name))]
    assert main(arguments(common)) == 4
    assert calls == ['append', 'checkpoint', 'witness'][:calls.index(stage) + 1]


@pytest.mark.parametrize('value', ['0', '9007199254740991'])
def test_amount_boundaries(value):
    from examples.transactions import amount
    assert amount(value) == int(value)
