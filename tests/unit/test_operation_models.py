"""Typed operation values own validated, immutable public evidence."""

from dataclasses import FrozenInstanceError

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.model.operations import Checkpoint, ExportResult, Manifest, WitnessResult
from tests.unit.test_verifier import _anchored


def values():
    manifest, _, checkpoints, receipts = _anchored(n=2, anchor_count=2)
    metadata = {'version': 1, 'type': 'export', 'log_id': manifest['body']['log_id'],
                'manifest_hash': manifest['manifest_hash'], 'through': 2, 'record_count': 2,
                'generated_at': '2026-11-10T00:00:00.000000Z'}
    return [manifest, checkpoints[0], receipts[0], metadata]


@pytest.mark.parametrize('index,model', list(enumerate([Manifest, Checkpoint, WitnessResult, ExportResult])))
def test_operation_models_own_inputs_and_returned_values(index, model):
    value = values()[index]
    result = model('bundle', value) if model is ExportResult else model(value)
    expected = result.to_dict()
    value.clear()
    returned = result.to_dict()
    returned.clear()
    if model is ExportResult:
        result.metadata.clear()
    else:
        result.body.clear()
    assert result.to_dict() == expected
    with pytest.raises(FrozenInstanceError):
        result._encoded = b'{}'


@pytest.mark.parametrize('index,model', list(enumerate([Manifest, Checkpoint, WitnessResult])))
@pytest.mark.parametrize('change', ['extra', 'missing', 'digest', 'signature', 'body', 'version'])
def test_envelope_models_reject_invalid_evidence(index, model, change):
    envelope = values()[index]
    if change == 'extra':
        envelope['secret'] = 'must-not-appear-in-error'
    elif change == 'missing':
        envelope.pop('body')
    elif change == 'digest':
        key = ['manifest_hash', 'checkpoint_hash', 'receipt_hash'][index]
        envelope[key] = 'ff' * 32
    elif change == 'signature':
        envelope['signature'] = 'short'
    elif change == 'body':
        envelope['body']['secret'] = 'must-not-appear-in-error'
    else:
        envelope['body']['version'] = 2
    with pytest.raises(CasfError) as error:
        model(envelope)
    assert 'must-not-appear-in-error' not in str(error.value)


@pytest.mark.parametrize('change', [{'through': True}, {'record_count': 1}, {'version': 2},
                                    {'type': 'wrong'}, {'extra': 1}])
def test_export_result_rejects_inconsistent_metadata(change):
    metadata = values()[3] | change
    with pytest.raises(CasfError):
        ExportResult('bundle', metadata)


def test_properties_expose_exact_checkpoint_and_receipt_identity():
    manifest, checkpoint, receipt, metadata = values()
    m, cp, result = Manifest(manifest), Checkpoint(checkpoint), WitnessResult(receipt)
    assert m.log_id == cp.log_id == result.log_id
    assert m.manifest_hash == manifest['manifest_hash']
    assert cp.checkpoint_hash == result.checkpoint_hash == checkpoint['checkpoint_hash']
    assert cp.index == 0 and cp.count == result.count == 2
    assert cp.final is False
    assert result.stored is True and result.witness_state.value == 'WITNESSED'
    assert result.receipt == receipt
    export = ExportResult('bundle', metadata)
    assert export.published is True and export.through == 2


def test_model_construction_does_not_authenticate_a_signature():
    # A well-formed forged signature is not trust: writer operations still verify it.
    manifest = values()[0]
    manifest['signature'] = crypto.b64url_encode(bytes(64))
    assert Manifest(manifest).to_dict() == manifest


@pytest.mark.parametrize('index,model,field', [
    (0, Manifest, 'issuer_id'), (0, Manifest, 'log_public_key'),
    (1, Checkpoint, 'head_hash'), (2, WitnessResult, 'checkpoint_hash'),
])
def test_protocol_strings_reject_trailing_newlines(index, model, field):
    envelope = values()[index]
    envelope['body'][field] += '\n'
    kind = ['manifest', 'checkpoint', 'receipt'][index]
    digest = [crypto.digest_manifest, crypto.digest_checkpoint, crypto.digest_receipt][index]
    envelope[kind + '_hash'] = digest(envelope['body'])
    with pytest.raises(CasfError):
        model(envelope)


def test_manifest_body_budget_is_enforced_before_crypto():
    from casf.errors import LimitError

    envelope = values()[0]
    envelope['body']['log_public_key'] = 'A' * 17000
    with pytest.raises(LimitError):
        Manifest(envelope)
