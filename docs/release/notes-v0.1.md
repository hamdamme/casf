# CASF 0.1.0rc1 release candidate notes

CASF 0.1.0rc1 is the proposed first experimental release candidate. It has
not been published. Publication needs a separate explicit approval.

CASF creates signed audit records, links them with SHA 256 hashes, and lets a
separate witness retain signed checkpoints. A verifier can check the record
chain offline, compare it with a trusted checkpoint, or query a witness for a
fresh signed view. This release candidate is intended for evaluation and
research, not as production security infrastructure.

## Included

- Python package and command line interface for writing, exporting, and
  verifying audit evidence.
- SQLite writer with transactional appends, retry handling, sealing, and key
  rotation support.
- HTTP witness service that validates extensions and retains signed receipts.
- Streaming command line verification with configured input and protocol
  limits.
- Integrity, anchored, and online verification modes with retained verifier
  state.
- Tests, protocol vectors, research methods, and historical benchmark data.

## Security and behavior notes

Every command line verification requires `--state PATH`. On the first
observation only, add `--initialize-state`. Later checks must use the same
state file and omit that option. Protect and back up verifier state separately
from the bundle and witness. See the [installation and usage guide](../installation.md)
and [verification guide](../verification.md).

Recent fixes prevent unsigned online errors from appearing as proof of
rollback, retain accepted history between command line runs, reject unsafe
HTTPS transport behavior, and reject a provisioned witness identity that does
not match the signed manifest. The witness identity regression test merged in
PR 20. The [Phase 3 closeout record](phase3-closeout-2026-10-28.md) lists the
findings, tests, and dispositions.

CASF does not prove that every event was recorded or that signed event claims
are true. Loss of an unwitnessed tail, a false suffix signed with a stolen
writer key, and some witness rollback cases remain outside its guarantees.
CASF has not received a formal security audit or proof. External feedback was
limited; the areas not examined are listed in the closeout record.

## Validation and research scope

The candidate install and command line rehearsal used temporary synthetic
evidence. That rehearsal verifies software behavior; it is not a research
result and is independent from the separate real file demonstration.

The recorded benchmark results belong to their original code versions,
machines, workloads, and network path. The maintainer accepts them as
historical research evidence only. They are not performance measurements of
0.1.0rc1 and do not establish general deployment throughput.

The release validation scope is macOS arm64 and Ubuntu 24.04 x86_64 with
CPython 3.12 through 3.14. Other systems and processor types have not been
validated for this candidate.

## Install

This candidate is not available from a package index. Do not use
`pip install casf` yet. If approved, the release notice will provide the exact
artifacts and their SHA 256 values. See the [candidate install guide](../installation.md).

## Approval status

The historical benchmark scope and limited external review are accepted for
the first experimental release, with their limitations recorded. The exact
candidate artifact hashes and notes still require maintainer approval.
Publication is not authorized by this document.
