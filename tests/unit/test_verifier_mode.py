"""R07: reject invalid mode arguments before evidence or bundle access."""

import json
from types import SimpleNamespace

import pytest

from casf.errors import CasfError
from casf.verifier import Mode, Result, verify, verify_bundle
from casf.verifier.report import FreshnessStatus
from tests.unit.test_incremental_verification import history
from tests.unit.test_streaming import public_pins
from tests.unit.test_verify_bundle import setup_bundle


@pytest.mark.parametrize('mode', ['integrity', 'anchored', 'online', None, 0, 1, True, object()])
def test_invalid_mode_rejected_before_evidence_consumption(mode):
    args = history()

    def forbidden():
        pytest.fail('invalid mode consumed evidence')
        yield

    for name in ('records', 'checkpoint_envelopes', 'receipt_envelopes', 'status_envelopes'):
        args[name] = forbidden()
    args['mode'] = mode
    with pytest.raises(ValueError, match='mode must be a Mode member'):
        verify(**args)


@pytest.mark.parametrize('mode', ['integrity', 'anchored', 'online', None, 0, 1, True, object()])
def test_invalid_bundle_mode_rejected_before_io(tmp_path, monkeypatch, mode):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid mode opened bundle')

    monkeypatch.setattr('casf.verifier.bundle.open_bundle', forbidden)
    with pytest.raises(ValueError, match='mode must be a Mode member'):
        verify_bundle(tmp_path / 'unopened', history()['pins'], mode)


def test_raw_online_cannot_pass_without_freshness_check():
    args = history()

    def forbidden():
        pytest.fail('invalid mode invoked callback')

    args.update(mode='online', online_query=forbidden)
    with pytest.raises(ValueError, match='mode must be a Mode member'):
        verify(**args)


@pytest.fixture(params=['direct', 'bundle'])
def invocation(request, tmp_path):
    if request.param == 'direct':
        args = history()
        checkpoint = args['checkpoint_envelopes'][-1]

        def call(mode, query):
            return verify(**dict(args, mode=mode, online_query=query))
    else:
        path, evidence, _ = setup_bundle(tmp_path, count=2)
        pins = public_pins(path)
        checkpoint = evidence.checkpoints[-1]

        def call(mode, query):
            return verify_bundle(path, pins, mode, online_query=query)
    return call, checkpoint


@pytest.mark.parametrize('mode', list(Mode))
def test_valid_modes_preserve_freshness_and_serialization(invocation, mode):
    call, checkpoint = invocation
    calls = []

    def query():
        calls.append(True)
        return SimpleNamespace(body={'checkpoint_index': checkpoint['body']['index'],
                                     'checkpoint_hash': checkpoint['checkpoint_hash']})

    report = call(mode, query)
    assert report.result is Result.PASS
    assert report.mode is mode
    assert json.loads(json.dumps(report.to_dict()))['mode'] == mode.value
    assert len(calls) == (1 if mode is Mode.ONLINE else 0)
    assert report.freshness_status is (
        FreshnessStatus.FRESH_WITNESS_VIEW if mode is Mode.ONLINE
        else FreshnessStatus.NOT_REQUESTED)


def test_valid_online_requires_query(invocation):
    call, _ = invocation
    with pytest.raises(CasfError, match='online mode requires an online_query callable'):
        call(Mode.ONLINE, None)
