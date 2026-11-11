# Repository review: PR 57

Base: `f6d5d031bada0bb93642bc3070da07dfb93205ae` (merged PR 56).
This completes the tracked-file review continuation for PR 57. Acceptance and
merge remain pending. Review does not certify absence of defects, replace previous
release evidence, or authorize a release.

## Reproduced findings and corrections

| Area | Finding | Correction and regression evidence |
| --- | --- | --- |
| Private keys | Loading followed symlinks and ignored permissions; failed writes could leave a destination file. | Owner-only regular files and parent directory, bounded reads, no symlink following, flushed temporary file and exclusive publication. `test_key_files.py` covers permissions, symlinks, write failure and overwrite preservation. |
| Protocol validation | The verifier accepted signed oversized record bodies; empty event fields passed request validation; malformed payloads could escape the report path. | Shared body limits and profile validation before cryptographic work; nonempty actor/event type; invalid-evidence reports. `test_protocol_boundaries.py` covers negative and boundary cases. |
| Retained status | Stale `StatusBook` objects could replace newer status or revocation; issuer mismatches and unknown status could be persisted. | Lock, reread, authenticate, preserve terminal revocation and serial high-water, flush and replace atomically. `test_status_book_safety.py` covers stale readers and invalid evidence. |
| Epoch continuity | Witness registration accepted successor manifests without authenticating predecessor evidence; rotation did not compare all receipt bindings. | Authenticate the old manifest, final checkpoint, receipt, keys and link before registration. Supplied old authority remains independently provisioned. `test_rotation_registration.py` covers absent/forged evidence and CLI rotation to a different witness. |
| Nesting boundary | Valid depth-16 record bodies failed when wrapped in an envelope for storage. | Count the envelope separately while preserving the body depth limit, including append and restore serialization. `test_protocol_boundaries.py` covers maximum-depth append and startup checks. |
| Submission encoding | ASCII escaping inflated valid Unicode records beyond wire budgets. | Compact UTF-8 submission encoding. `test_submission_encoding.py` checks wire size and successful receipt storage. |
| Transport cleanup | Deadline expiry between connection and request setup leaked the connected socket. | Own the socket through setup and close it on every failure path; two deadline-boundary regressions in `test_online_transport.py`. |

Non-object witness records now fail as schema errors rather than internal service
errors. No cryptographic domains, signatures, historical measurements, frozen
vectors or published release assets were replaced.

Additional corrections from the remaining-file review:

- Benchmark warmup now drains every checkpoint before measurement; HTTP retries
  are counted at one layer. Invalid batch sizes fail before creating stores.
- H1 retains each trial as it finishes, records setup failures as invalid trials,
  returns failure for invalid experiments, and only retains a pin after a passing
  healthy control. The original unmet primary hypothesis is unchanged.
- H3 closes resources on setup failure, restores the caller's environment, and
  reports incomplete pilots without claiming feasibility.
- Streaming fixture generation preserves existing trust files; benchmark server
  construction closes its service after listener failure.
- Two crash tests previously accepted startup failure as the intended crash.
  They now require a distinct exit code from the exact hook; the post-commit case
  inspects the stored record before retry. Concurrent child exits and retained
  report-state assertions are also checked.
- The recovery guide no longer lists implemented typed operations and reports as
  future work. Experiment rerun instructions preserve historical output.

## Coverage and reuse

The [file register](repository-files.json) accounts for all **512 tracked paths**:

| Method | Files | Scope |
| --- | ---: | --- |
| Manual text reading | 266 | All Python and Markdown, policies/configuration, SQL fixtures and SVG source. Includes all 38 runtime Python files. |
| Structured data review | 243 | 237 JSON files, five checksum lists and the dependency lock. Field meanings, all-record validation, recomputation and provenance checks; not a claim of manually reading every numeric or digest line. |
| Document text and visual review | 3 | Both Word documents and the tracked PDF; all 12 historical Word pages, 11 preprint Word pages and 11 PDF pages. SVG rendering also inspected. |

No tracked path is left without a review method. The original prototype Word
file remains a clearly marked archive, with formatting defects documented in
[its README](../historical/README.md). The preprint and frozen evidence retain
their original bytes and historical claims. No new DOI, manuscript approval or
production readiness is implied.

Data checks traversed all 237 JSON files for duplicate keys and nonfinite values.
They checked all 582,170 append/submission timing values across 120 run files,
recomputed all 48 metric rows and bootstrap intervals in the 12 configuration
reports, reconciled all 62 H3 runs (1,984 event rows) with their checkpoint timing,
backlog, outage/recovery records and paired summaries, checked H1 outcomes and
classifications and the two detection matrices, and recomputed both RQ4 snapshots
from their recorded commits. All 96 streaming runs have unique case identities,
matching input digests and consistent result/time/memory fields.

The 193-entry historical inventory matches its measurement revision; current
research publication/source digests match their retained files and source commit.
The published three-asset cache, every wheel/archive member hash, 46 packaged
inputs, and installed runtime digests reconcile with the release records. All
25 recorded advisory queries reconcile with the unchanged locked package set;
this reuses their dated responses, not a new advisory-service query. The lock's
442 artifact records use the expected registry, HTTPS artifact host, SHA-256
format and positive sizes.

Prior per-file structural checks and dated release/research results remain
credited only for their original bytes and scope. Raw-data validation cannot
independently establish how an old experiment was conducted.

## Validation

On macOS arm64 with Python 3.12.14 and locked dependencies:

- Full current-source suite: **1,256 passed** in 97.11 seconds. PR 57 adds 53
  cases relative to the 1,203-test base; the continuation adds 16.
- The final assertion-map/import-order edits passed 17 focused checks.
- Ruff, strict mypy, lock validation and package inspection passed.
- Repository consistency checks cover every tracked file and local Markdown link.
- The prior 6,075-case parser campaigns and fresh-wheel 21-check demo cover
  unchanged runtime bytes; packaging is checked again after this continuation.
- The previous PR head `d5562c4` passed all twelve hosted configurations in
  [run 43084289801](https://github.com/hamdamme/casf/actions/runs/43084289801).
  Final-head checks are reported on PR 57 separately.

## Limits and remaining work

The review is complete by the methods above; it is **not** a literal manual
reading of every repeated data value or proof that the project has no bugs.
The following are not verified by this review:

- Current availability/correctness of every external reference or a fresh
  dependency advisory query; hidden/untracked local files and every Git revision.
- Independent reproduction of all historical measurements or historical host
  conditions. H1's primary predeclared result remains unmet and documented.
- A new physical Linux-laptop run. Hosted Linux tests are separate evidence.
- Independent security review, physical power-loss durability, persistent
  cross-host TLS deployment, administrative separation or real-data retention.

F19, F20 and F28 await review of PR 57. The published `0.1.0rc2` files do not
contain these fixes. No merge, replacement release or PyPI publication is part
of this review.
