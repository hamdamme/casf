"""Replay a bounded corpus and mutate synthetic JSON without hiding crashes."""

import hashlib
import json
import random
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from casf.canonical.jcs import canonicalize, parse, parse_config
from casf.errors import CasfError

MAX_INPUT_BYTES = 131072
MAX_CASES = 100000
SECRET_MARKER = 'synthetic-secret-marker'
CORPUS = Path(__file__).with_name('corpus.json')


@dataclass(frozen=True)
class Case:
    name: str
    target: str
    data: bytes
    expected: str | None = None


class CampaignFailure(Exception):
    """A reproducible unexpected outcome, saved outside the source corpus."""

    def __init__(self, artifact, category):
        self.artifact, self.category = artifact, category
        super().__init__(f'{category}; replay input: {artifact}')


def load_corpus(path=CORPUS):
    with Path(path).open('rb') as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('corpus exceeds 1 MiB')
    entries = json.loads(raw)
    cases = []
    for entry in entries:
        if 'hex' in entry:
            data = bytes.fromhex(entry['hex'])
        elif 'parts' in entry:
            chunks = []
            total = 0
            for part in entry['parts']:
                text, repeat = part['text'].encode(), part.get('repeat', 1)
                if type(repeat) is not int or repeat < 0:
                    raise ValueError('invalid corpus repetition')
                total += len(text) * repeat
                if total > MAX_INPUT_BYTES:
                    raise ValueError('corpus input exceeds byte limit')
                chunks.append(text * repeat)
            data = b''.join(chunks)
        else:
            data = entry['text'].encode()
        if len(data) > MAX_INPUT_BYTES or entry['target'] not in ('wire', 'config'):
            raise ValueError('invalid corpus target or input size')
        cases.append(Case(entry['name'], entry['target'], data, entry['expected']))
    if not cases or len({case.name for case in cases}) != len(cases):
        raise ValueError('corpus must contain uniquely named inputs')
    return cases


def exercise(target, data):
    """Only documented CASF rejections are normal; all other failures escape."""
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError('fuzz input exceeds byte limit')
    try:
        if target == 'wire':
            value = parse(data)
            encoded = canonicalize(value)
            assert parse(encoded) == value
            assert canonicalize(parse(encoded)) == encoded
        elif target == 'config':
            value = parse_config(data)
            encoded = json.dumps(value, ensure_ascii=True, allow_nan=False)
            assert parse_config(encoded) == value
        else:
            raise ValueError('unknown fuzz target')
    except CasfError as exc:
        assert SECRET_MARKER not in str(exc), 'parser diagnostic exposed input'
        return type(exc).__name__
    return 'accepted'


def mutate(data, rng):
    """One deterministic byte mutation, capped before entering the parser."""
    offset = rng.randrange(len(data) + 1)
    end = rng.randrange(offset, len(data) + 1)
    token = rng.choice([b'"', b'\\ud800', b'-0', b'9' * 17, b':', b',', b'\x00',
                        b'\xff', b'[]', b'{}', b'true', SECRET_MARKER.encode()])
    operation = rng.randrange(6)
    if operation == 0:
        result = data[:offset] + token + data[offset:]
    elif operation == 1:
        result = data[:offset] + data[end:]
    elif operation == 2:
        result = data[:offset] + bytes([rng.randrange(256)]) + data[offset + 1:]
    elif operation == 3:
        result = data[:offset]
    elif operation == 4:
        result = data[:offset] + data[offset:end] + data[offset:]
    else:
        depth = rng.randrange(1, 33)
        result = b'[' * depth + data + b']' * depth
    return result[:MAX_INPUT_BYTES]


def minimize(case, category, deadline, max_attempts=128):
    """Delete chunks while retaining the same unexpected failure category."""
    data, attempts, pieces = case.data, 0, 2
    while data and attempts < max_attempts and time.monotonic() < deadline:
        size = max(1, (len(data) + pieces - 1) // pieces)
        reduced = False
        for offset in range(0, len(data), size):
            if attempts >= max_attempts or time.monotonic() >= deadline:
                return replace(case, data=data), attempts
            candidate = data[:offset] + data[offset + size:]
            attempts += 1
            try:
                exercise(case.target, candidate)
            except Exception as exc:  # noqa: BLE001 - preserve the original failure category.
                if type(exc).__name__ == category:
                    data, pieces, reduced = candidate, max(2, pieces - 1), True
                    break
        if not reduced:
            if size == 1:
                break
            pieces = min(len(data), pieces * 2)
    return replace(case, data=data), attempts


def save_failure(case, original, category, directory, seed, iteration, attempts):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(case.target.encode() + b'\0' + case.data).hexdigest()
    path = directory / (digest + '.json')
    artifact = {'version': 1, 'target': case.target, 'data_hex': case.data.hex(),
                'failure': category, 'seed': seed, 'iteration': iteration,
                'corpus_name': case.name, 'original_bytes': len(original),
                'original_sha256': hashlib.sha256(original).hexdigest(),
                'saved_bytes': len(case.data), 'shrink_attempts': attempts}
    # Refuse replacement; repeated discoveries retain their first provenance.
    try:
        with path.open('x') as output:
            json.dump(artifact, output, indent=2)
            output.write('\n')
    except FileExistsError:
        pass
    return path


def run_campaign(*, seed, cases, failures, seconds=60, corpus=CORPUS):
    if type(cases) is not int or not 1 <= cases <= MAX_CASES:
        raise ValueError('cases must be between 1 and 100000')
    if type(seconds) is not int or not 1 <= seconds <= 3600:
        raise ValueError('seconds must be between 1 and 3600')
    if type(seed) is not int or not 0 <= seed <= 2**64 - 1:
        raise ValueError('seed must be an unsigned 64-bit integer')
    seeds = load_corpus(corpus)
    rng, counts, digest = random.Random(seed), Counter(), hashlib.sha256()
    deadline = time.monotonic() + seconds
    for index in range(len(seeds) + cases):
        if time.monotonic() >= deadline:
            raise TimeoutError('campaign deadline exceeded before completing all cases')
        baseline = index < len(seeds)
        source = seeds[index] if baseline else rng.choice(seeds)
        case = source if baseline else replace(source, data=mutate(source.data, rng), expected=None)
        try:
            outcome = exercise(case.target, case.data)
            if case.expected is not None:
                assert outcome == case.expected, 'corpus outcome changed'
        except Exception as exc:
            category = type(exc).__name__
            original = case.data
            # Exact corpus expectations have their own oracle; deleting bytes
            # would invalidate it. Only unexpected mutation failures shrink.
            minimized, attempts = (case, 0) if baseline else minimize(case, category, deadline)
            artifact = save_failure(minimized, original, category, failures, seed, index, attempts)
            raise CampaignFailure(artifact, category) from exc
        counts[case.target + ':' + outcome] += 1
        digest.update(case.target.encode() + b'\0' + len(case.data).to_bytes(4, 'big') + case.data)
    if time.monotonic() >= deadline:
        raise TimeoutError('campaign deadline exceeded before completion')
    return {'seed': seed, 'corpus_cases': len(seeds), 'mutation_cases': cases,
            'completed_cases': len(seeds) + cases, 'max_input_bytes': MAX_INPUT_BYTES,
            'input_sha256': digest.hexdigest(), 'outcomes': dict(sorted(counts.items()))}
