"""Corpus outcomes, reproducibility, resource bounds and failure preservation."""

import json
import random
import time

import pytest

from tests.fuzz import runner
from tests.fuzz.__main__ import main


@pytest.mark.parametrize('case', runner.load_corpus(), ids=lambda case: case.name)
def test_parser_regression_corpus(case):
    assert runner.exercise(case.target, case.data) == case.expected


def test_seeded_campaign_replays_identical_input(tmp_path):
    first = runner.run_campaign(seed=17, cases=250, failures=tmp_path)
    replay = runner.run_campaign(seed=17, cases=250, failures=tmp_path)
    other = runner.run_campaign(seed=18, cases=250, failures=tmp_path)
    assert first == replay
    assert first['input_sha256'] != other['input_sha256']
    assert first['completed_cases'] == 250 + first['corpus_cases']
    assert sum(first['outcomes'].values()) == first['completed_cases']
    assert first['outcomes']['wire:accepted'] > 0
    assert first['outcomes']['config:accepted'] > 0
    assert not list(tmp_path.iterdir())


def test_mutations_respect_input_size_ceiling():
    rng = random.Random(17)
    for data in (b'', b'{}', b'a' * runner.MAX_INPUT_BYTES):
        for _ in range(100):
            assert len(runner.mutate(data, rng)) <= runner.MAX_INPUT_BYTES


def test_unexpected_mutation_is_minimized_saved_and_replayable(tmp_path, monkeypatch):
    original = runner.exercise

    def crashing(target, data):
        if b'X' in data:
            raise RuntimeError('synthetic parser crash')
        return original(target, data)

    monkeypatch.setattr(runner, 'exercise', crashing)
    monkeypatch.setattr(runner, 'mutate', lambda data, rng: b'prefix-X-suffix')
    with pytest.raises(runner.CampaignFailure) as caught:
        runner.run_campaign(seed=17, cases=1, failures=tmp_path)
    artifact = json.loads(caught.value.artifact.read_text())
    assert artifact['failure'] == 'RuntimeError'
    assert artifact['shrink_attempts'] <= 128
    assert artifact['saved_bytes'] == 1 < artifact['original_bytes']
    assert bytes.fromhex(artifact['data_hex']) == b'X'
    with pytest.raises(RuntimeError, match='synthetic parser crash'):
        runner.exercise(artifact['target'], bytes.fromhex(artifact['data_hex']))


def test_changed_corpus_expectation_preserves_exact_input(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'load_corpus', lambda _: [runner.Case('known', 'wire', b'null', 'wrong')])
    with pytest.raises(runner.CampaignFailure) as caught:
        runner.run_campaign(seed=17, cases=1, failures=tmp_path)
    artifact = json.loads(caught.value.artifact.read_text())
    assert artifact['data_hex'] == b'null'.hex()
    assert artifact['shrink_attempts'] == 0


def test_shrinking_never_exceeds_attempt_budget(monkeypatch):
    def crashing(target, data):
        raise RuntimeError('synthetic crash on every input')

    monkeypatch.setattr(runner, 'exercise', crashing)
    result, attempts = runner.minimize(runner.Case('case', 'wire', b'x' * 1000),
                                      'RuntimeError', time.monotonic() + 10, max_attempts=3)
    assert attempts == 3
    assert len(result.data) < 1000


def test_deadline_cannot_report_partial_campaign_success(tmp_path, monkeypatch):
    ticks = iter([0, 0, 2])
    monkeypatch.setattr(runner.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(TimeoutError):
        runner.run_campaign(seed=17, cases=1, seconds=1, failures=tmp_path)


@pytest.mark.parametrize('options', [{'cases': 0}, {'cases': runner.MAX_CASES + 1},
                                   {'cases': True}, {'seconds': 0}, {'seed': -1}])
def test_campaign_rejects_invalid_budgets(tmp_path, options):
    args = {'seed': 17, 'cases': 1, 'seconds': 10, 'failures': tmp_path}
    args.update(options)
    with pytest.raises(ValueError):
        runner.run_campaign(**args)


def test_cli_reports_failure_artifact_and_successful_replay(tmp_path, monkeypatch, capsys):
    import tests.fuzz.__main__ as cli

    path = runner.save_failure(runner.Case('case', 'wire', b'null'), b'null',
                               'RuntimeError', tmp_path, 17, 0, 0)

    def failed(**kwargs):
        raise runner.CampaignFailure(path, 'RuntimeError')

    monkeypatch.setattr(cli, 'run_campaign', failed)
    assert main(['--cases', '1', '--failures', str(tmp_path)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['result'] == 'FAIL' and result['replay'] == str(path)
    assert main(['--replay', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['outcome'] == 'accepted'


def test_failure_artifact_is_not_overwritten(tmp_path):
    case = runner.Case('case', 'wire', b'null')
    first = runner.save_failure(case, b'null', 'RuntimeError', tmp_path, 17, 0, 0)
    original = first.read_bytes()
    assert runner.save_failure(case, b'null', 'RuntimeError', tmp_path, 99, 1, 0) == first
    assert first.read_bytes() == original
