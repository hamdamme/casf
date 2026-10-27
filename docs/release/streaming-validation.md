# Streaming verification validation

Recorded 2026-10-27. Baseline: `1c7b7ee`. Scope: record memory and bounded
checkpoint head comparisons under SPEC Sections 5, 15, and 20.

## Implementation review

The original reader retained all decoded records. The verifier additionally
retained one digest per verified record. Checkpoint tuples, receipt bodies,
receipt matches, and evidence lists were also retained, but had explicit
protocol object and traversal limits. Diagnostic codes have a fixed vocabulary;
they do not accumulate one diagnostic per record. The CLI did not need its
own record list, but inherited the eager reader allocation.

`open_bundle` now owns the file and yields records sequentially. The CLI uses
that path. `verify` keeps a running count and head plus digests only for counts
requested by at most `max_chain_steps` checkpoint envelopes. All original
checkpoint, receipt, status, chain, signature, and freshness checks remain.
The [API decision](../adr/ADR-006-streaming-verification.md) explains bounds,
error timing, and compatibility. `read_bundle` and restore intentionally remain
eager; users must choose the streaming entry point for bounded record memory.

## Completed local validation

- Full suite: 354 passed on macOS ARM, Python 3.13.17.
- Lint passed for source, tests, and the new measurement harness.
- Strict typing passed for all 23 source files; whitespace checks passed.
- The dependency lock check passed without changing dependencies.
- Wheel and source archive builds passed using the existing locked environment.
- A fresh wheel environment passed base import and optional dependency checks,
  public streaming verification, and the local witness request and shutdown check.
- The original 123 protected backup, research, vector, and benchmark files
  matched the preservation baseline.

The supported GitHub matrix checks Python 3.12, 3.13, and 3.14 with locked and
minimum direct dependencies, including package installation checks. Successful
results for the submitted head must be confirmed in the pull request checks;
the local results above do not substitute for that confirmation.

New regressions cover empty and small logs, multiple checkpoint batches, valid
online views with retained state, malformed JSONL, metadata truncation, altered,
missing, duplicated and reordered records, line/count/byte budgets, repeated
checkpoint counts, intermediate checkpoint divergence, descriptor closure,
record path replacement, and late CLI read errors before state saving.
Existing tests continue covering restored witnesses, divergent histories,
revocation, signatures, protocol budgets, and all verification modes.

An additional development comparison against the original verifier produced
identical values for every report field in 411 cases across integrity, anchored,
and online modes. It used valid and individually altered record, checkpoint,
receipt, and status envelopes and truncated streams. This finite comparison
and passing tests are regression evidence, not a formal security proof or an
independent audit.

## Memory and performance

The [measurement report](../../benchmarks/results/streaming-v1/report.md)
includes the complete procedure, source hashes, input hashes, and all 96 run
records. Inputs were generated before measurement. Python allocation peaks
were measured separately from ordinary execution timing.

For anchored verification with a fixed checkpoint prefix, peak traced memory
at 128, 2048, and 16384 records was 0.315, 0.318, and 0.318 MiB. The baseline
was 0.759, 7.634, and 58.802 MiB. With a growing chain of 128 checkpoints at
16384 records, the candidate used 0.916 MiB versus 59.355 MiB before.
At 16384 records, median time changes across measured configurations ranged
from about 3 percent faster to 1 percent slower. No meaningful performance
regression was observed in this limited comparison.

The implementation bound is O(R + E + C): one decoded record and parser
workspace R, bounded decoded protocol evidence E, and at most C checkpoint
boundary digests. Actual memory increases with protocol evidence within its
configured ceilings. Raising the evidence or traversal budgets raises those
ceilings. This does not claim constant memory for unlimited protocol history.
The eager compatibility reader still has O(N) record storage by design.

## Remaining limits

Memory evidence is limited to these controlled workloads and machine. Traced
Python memory excludes native allocations and filesystem caches; process RSS
is separately recorded with its platform units. No online network performance
or concurrent throughput conclusion is drawn. Bundle mutation during reading
is unsupported and no filesystem snapshot guarantee is added.

The streaming verification requirement is supported within the documented
per record and bounded protocol state model. External reviewer confirmation,
platform and redistribution review, final candidate rehearsal, and maintainer
release approval remain separate gates. No release or merge is authorized by
this validation record.
