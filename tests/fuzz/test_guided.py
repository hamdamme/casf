"""R01/R10: coverage feedback, retained bounds and failure replay are observable."""

import json
import sys
from pathlib import Path

import pytest

from tests.fuzz import guided
from tests.fuzz.runner import CampaignFailure


def test_measured_follows_new_branch_and_restores_trace():
    def branch(value):
        if value:
            return 1
        return 0
    previous = sys.gettrace()
    first, left = guided.measured(lambda: branch(True), root=Path(__file__).parent)
    second, right = guided.measured(lambda: branch(False), root=Path(__file__).parent)
    assert (first, second) == (1, 0)
    assert left - right and right - left
    assert sys.gettrace() is previous
    with pytest.raises(ZeroDivisionError):
        guided.measured(lambda: 1 / 0)
    assert sys.gettrace() is previous


def test_guided_campaign_retains_new_paths_and_is_repeatable(tmp_path):
    first = guided.run_guided(seed=42, cases=100, failures=tmp_path)
    second = guided.run_guided(seed=42, cases=100, failures=tmp_path)
    assert first == second
    assert first['completed_cases'] == first['corpus_cases'] + 100
    assert first['python_edges'] > 0
    assert first['novel_mutations'] > 0
    assert first['corpus_cases'] < first['retained_inputs'] <= guided.MAX_POOL


def test_guided_unexpected_failure_is_replayable(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(guided, 'exercise', broken)
    with pytest.raises(CampaignFailure) as caught:
        guided.run_guided(seed=1, cases=1, failures=tmp_path)
    saved = json.loads(caught.value.artifact.read_text())
    assert saved['failure'] == 'RuntimeError'
    assert bytes.fromhex(saved['data_hex']) == guided.load_corpus()[0].data


@pytest.mark.parametrize('value', [True, 0, -1, 100001])
def test_guided_rejects_invalid_case_budget(value, tmp_path):
    with pytest.raises(ValueError):
        guided.run_guided(seed=1, cases=value, failures=tmp_path)


def test_guided_pool_stays_bounded_after_new_paths(tmp_path, monkeypatch):
    limit = len(guided.load_corpus()) + 1
    monkeypatch.setattr(guided, 'MAX_POOL', limit)
    result = guided.run_guided(seed=42, cases=100, failures=tmp_path)
    assert result['novel_mutations'] > 1
    assert result['retained_inputs'] == limit


def test_guided_deadline_is_not_a_success(tmp_path, monkeypatch):
    ticks = iter([0, 61])
    monkeypatch.setattr(guided.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(TimeoutError):
        guided.run_guided(seed=1, cases=1, failures=tmp_path)
