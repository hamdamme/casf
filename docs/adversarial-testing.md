# Generated inputs and parser fuzzing

The current suite exercises serialization and record-history properties with
Hypothesis, and runs bounded byte mutations against the wire JSON and
configuration JSON parsers. These checks supplement deterministic regressions;
they do not establish full protocol coverage, formal proof or penetration testing.

## Run the checks

Use the locked development environment described in [installation](installation.md).
From the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/property tests/fuzz -v --hypothesis-show-statistics
PYTHONPATH=src .venv/bin/python -m tests.fuzz --seed 20261110 --cases 2000 --failures /tmp/casf-fuzz
PYTHONPATH=src .venv/bin/python -m tests.fuzz --guided --seed 20261112 --cases 2000 --failures /tmp/casf-guided
```

All 12 Ubuntu/macOS CI jobs execute the properties and corpus replays. Each job
also runs three mutation campaigns with seeds `20261110`, `47` and
`9007199254740991`, each containing 2000 mutations plus the 25 seed cases.
The six locked-dependency jobs also run a guided campaign with seed `20261112`,
2,000 mutations and 25 seed cases. The minimum-runtime jobs use the same fixed Hypothesis tooling version as the
lockfile; they still resolve the lowest supported direct runtime dependencies.

## Property coverage

| Area | Generated inputs and assertions |
| --- | --- |
| Canonical JSON | Nested values, Unicode names, insertion-order permutations, safe integers, escaped duplicate names, forbidden numeric forms, lone surrogates, exact container depth and UTF-8 byte limits. Canonical output roundtrips and agrees with the standard JSON decoder. |
| Record histories | Synthetic signed histories of 1–12 records with generated payloads. Delete, duplicate, swap, body/digest/signature mutation and signed bad linkage must produce the expected failure code and absolute position. |
| Trusted prefixes | Full and incremental checks agree on checkpoint identity and coverage; the incremental range excludes the trusted prefix. Truncation can pass integrity but fails against a newer authenticated checkpoint. |
| Writer/witness recovery | Forty generated operation sequences with at most 30 steps each: append retries, pending checkpoints, lost/duplicate replies, forged receipts, restarts and backup inspection. The model compares record bytes, pending bytes and accepted witness heads after each step. |
| Work budgets | Record iteration consumes at most the configured count plus one sentinel and never reports a complete pass after budget exhaustion. |

The [shared settings](../tests/property/strategies.py) request up to 100
successful examples per property, with deterministic generation, no example
database and no per-example timing threshold. Finite strategies can exhaust
before that number; CI prints actual Hypothesis statistics. Reproduction depends
on the Python/Hypothesis versions and test source. Additional local exploration
can use `--hypothesis-seed=NUMBER` and should retain any discovered regression.
These choices follow the [Hypothesis settings contract](https://hypothesis.readthedocs.io/en/latest/settings.html).

The standard JSON decoder comparison checks interpretation, not independent
RFC 8785 certification. Frozen byte/signature vectors remain separate checks.
Verifier/canonicalization properties and the separate recovery state machine
cover selected transitions, not every writer/witness protocol state or crash
schedule. The separate [process matrix](process-crash-testing.md) exercises
named crash boundaries with parent-controlled kills.

## Fuzz bounds and evidence

The [committed corpus](../tests/fuzz/corpus.json) has positive inputs and
specific rejection expectations for both parsers. It includes malformed UTF-8,
BOMs, duplicate/escaped names, forbidden numbers, lone surrogates, oversized
keys, long integer tokens, deeply nested arrays and diagnostic secret markers.
Inputs use synthetic values only. Every ordinary pytest run replays the corpus.

The mutation runner inserts, deletes, replaces, truncates, duplicates or wraps
bytes. Each parser input is capped at 128 KiB. A campaign accepts at most
100000 mutations and a configurable 1–3600 second cooperative deadline
(default 60 seconds); it fails as incomplete if the deadline prevents the
requested count. CI additionally enforces a two-minute timeout on each job's
campaign step. The local deadline is checked between cases and shrink
attempts; it cannot interrupt a single hung parser call.

Only documented `CasfError` rejections are ordinary outcomes. Unexpected
exceptions and invariant failures fail the campaign. Summaries include seed,
completed counts, outcome categories and a digest of the actual input stream.
An unexpected mutation is reduced by deleting chunks while retaining its
failure category, for at most 128 attempts within the same deadline. This
bounded reduction does not promise a globally smallest input or identical root
cause; review the result before promoting it. A changed corpus expectation
preserves the exact original input because deleting bytes would change its oracle.

Failures are saved as JSON containing the target, input bytes in hex, category,
seed, iteration and reduction provenance. They are never silently overwritten.
To replay a saved input:

```bash
PYTHONPATH=src .venv/bin/python -m tests.fuzz --replay /tmp/casf-fuzz/INPUT_HASH.json
```

Replay runs the saved bytes against current code. A normal parser acceptance or
documented rejection succeeds after the bug is fixed; an unexpected failure
remains nonzero. Record the intended outcome as a named corpus case and add a
focused regression before accepting a fix. Hypothesis findings should likewise
be reduced and committed as explicit examples or ordinary tests; its transient
example database is not the regression record.

CI uploads summaries and any saved failures as `parser-fuzz-locked-RUNNER-VERSION`
and `parser-fuzz-minimum-RUNNER-VERSION` artifacts with 14-day retention, including
when a campaign fails. Download and review a finding before that retention
expires; accepted cases belong in the committed corpus. A hard timeout may
interrupt before a failure artifact can be saved. The JSON campaign summaries
remain in the job logs as well.

## Findings retained in this batch

The [parser regressions](../tests/unit/test_parser_regressions.py) preserve four
reproduced defects: object keys escaped the UTF-8 length limit; a 4301-digit
integer raised an interpreter ValueError; deep wire arrays raised
RecursionError; and duplicate-name diagnostics echoed input. The implementation
now enforces the key limit, rejects oversized integers before conversion,
normalizes parser recursion failures to LimitError, and omits input from those
diagnostics. Valid casf-v1 bytes and frozen vectors are unchanged.

The default campaign uses deterministic mutation. `--guided` adds Python
line-edge feedback within CASF modules and retains mutations that reach new
paths, with at most 256 retained inputs. It restores the previous tracing state
even after failure and refuses optimized Python execution. Its summary records
actual edge, discovery and retained-input counts. See the
[recorded campaign](release/guided-fuzz-2026-11-12.json). Neither runner fuzzes
HTTP framing, SQLite files, native cryptographic internals or every protocol
state transition. The [coverage status](release/test-coverage-status.md)
and [completion tracker](release/completion-tracker.md) retain those boundaries.
