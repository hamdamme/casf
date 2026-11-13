"""Bounded Python-edge-guided parser mutation; no native-code instrumentation."""

import random
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import casf
from tests.fuzz.runner import (
    CORPUS,
    MAX_CASES,
    MAX_INPUT_BYTES,
    CampaignFailure,
    exercise,
    load_corpus,
    minimize,
    mutate,
    save_failure,
)

ROOT = Path(casf.__file__).resolve().parent
MAX_POOL = 256


def measured(call, *, root=ROOT):
    """Collect consecutive Python line edges; restore any caller trace on failure."""
    edges, previous, filenames = set(), {}, {}
    prefix = str(root) + '/'

    def trace(frame, event, arg):
        filename = frame.f_code.co_filename
        if filename not in filenames:
            filenames[filename] = filename[len(prefix):] if filename.startswith(prefix) else None
        relative = filenames[filename]
        if relative is None:
            return None
        if event == 'line':
            edges.add((relative, previous.get(frame, 0), frame.f_lineno))
            previous[frame] = frame.f_lineno
        elif event == 'return':
            previous.pop(frame, None)
        return trace

    original = sys.gettrace()
    try:
        sys.settrace(trace)
        return call(), edges
    finally:
        sys.settrace(original)
        previous.clear()


def run_guided(*, seed, cases, failures, seconds=60, corpus=CORPUS):
    if not __debug__:
        raise ValueError('guided campaign requires assertion checks')
    for value, lower, upper in ((seed, 0, 2**64 - 1), (cases, 1, MAX_CASES),
                                (seconds, 1, 3600)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError('invalid guided campaign budget')
    pool = load_corpus(corpus)
    if len(pool) >= MAX_POOL:
        raise ValueError('seed corpus exceeds guided pool bound')
    baseline_count = len(pool)
    rng, seen, outcomes = random.Random(seed), set(), Counter()
    discoveries = 0
    deadline = time.monotonic() + seconds
    for index in range(baseline_count + cases):
        if time.monotonic() >= deadline:
            raise TimeoutError('guided campaign deadline exceeded')
        baseline = index < baseline_count
        source = pool[index] if baseline else rng.choice(pool)
        case = source if baseline else replace(source, data=mutate(source.data, rng), expected=None)
        try:
            outcome, edges = measured(lambda case=case: exercise(case.target, case.data))
            if case.expected is not None:
                assert outcome == case.expected, 'corpus outcome changed'
        except Exception as exc:
            category = type(exc).__name__
            minimized, attempts = (case, 0) if baseline else minimize(case, category, deadline)
            artifact = save_failure(minimized, case.data, category, failures, seed, index, attempts)
            raise CampaignFailure(artifact, category) from exc
        novel = edges - seen
        seen.update(edges)
        if novel and not baseline:
            discoveries += 1
            if len(pool) < MAX_POOL:
                pool.append(case)
            else:
                pool[rng.randrange(baseline_count, MAX_POOL)] = case
        outcomes[case.target + ':' + outcome] += 1
    if time.monotonic() >= deadline:
        raise TimeoutError('guided campaign deadline exceeded')
    return {'seed': seed, 'corpus_cases': baseline_count, 'mutation_cases': cases,
            'completed_cases': baseline_count + cases, 'python_edges': len(seen),
            'novel_mutations': discoveries, 'retained_inputs': len(pool),
            'max_retained_inputs': MAX_POOL, 'max_input_bytes': MAX_INPUT_BYTES,
            'outcomes': dict(sorted(outcomes.items()))}
