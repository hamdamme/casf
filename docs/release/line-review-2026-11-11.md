# Repository line review: work in progress

Base: `f6d5d031bada0bb93642bc3070da07dfb93205ae` (merged PR 56).
This continues the original repository review. It does not certify the repository
as complete, replace previous release evidence, or authorize a release.

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

## Coverage and reuse

The [file register](repository-files.json) identifies manual coverage for every
tracked path. `complete` means the entire text was read in this pass; line ranges
mean partial reading; `unchecked` means no complete manual reading in this pass.
These labels do not imply a second independent review or absence of bugs.
Prior per-file structural checks and dated release/research results remain
credited only for their original bytes and scope.

All 38 runtime Python files, the package typing marker, the governing
specification and selected guides, checks and tests have been read. Automated
repository checks parse/read all tracked files, validate local links, restore
SQL fixtures, inspect document containers and verify retained checksums. Those
checks do not constitute manual review of every line or every measurement.

## Validation

Final local results are recorded after the checks complete. The published
`0.1.0rc2` files do not contain these fixes. Prior Linux and twelve-configuration
CI results cannot be reused as validation of changed runtime bytes.

## Still unchecked

- The file register's `unchecked` paths and unlisted ranges in partial files:
  most existing tests, benchmark implementation and historical/research documents
  still need manual semantic review. Executing a test is not reviewing its assertions.
- Every raw measurement's meaning and complete recomputation of all historical
  reports. Structured parsing and checksum preservation establish different facts.
- Fresh visual inspection of all Word/PDF pages and the SVG; previous text and
  container checks remain separate evidence.
- Current availability and correctness of every external reference, dependency
  advisory refresh, hidden/untracked local files, and every historical Git revision.
- Changed-source Linux/Python 3.13/3.14 and minimum-dependency execution until new
  hosted results are verified; no fresh Linux-laptop run has occurred here.
- Independent security review, physical power-loss durability, production TLS,
  administration separation and real-data retention policy.

The tracker remains open. These source fixes are reviewable progress, not a
completed every-file audit or a production-readiness claim.
