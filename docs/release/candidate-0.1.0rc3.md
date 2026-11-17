# Initial experimental 0.1.0rc3 candidate record

**Superseded for current artifact review by the [c38bf82 refresh](candidate-0.1.0rc3-c38bf82.md).**
The original build evidence below remains historical.

Prepared 16 November 2026 (17 November UTC), **unpublished and awaiting review**.
Baseline main was PR 72 merge `40382b1ed5355fef9b7716919a7c141037528455`;
its [post-merge CI](https://github.com/hamdamme/casf/actions/runs/43994726679)
passed all twelve jobs. No open PRs existed at preparation start. The only
published release was rc2; its assets, tag and publication record are unchanged.

The files below were built from clean committed source
`a0ac1bfa61d3406c99b6bf758c62f6e840b633f3`, exported with `git archive`.
Later evidence-only documentation commits are not build inputs. No release tag,
GitHub release or PyPI upload has been created. The next publication requires
separate approval of the exact files and notes.

## Identified files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc3-py3-none-any.whl` | 108894 | `0cab3373d92476d46ea99bdce4cca4b37c9053e03d374c58de6ca3b276c331a6` |
| `casf-0.1.0rc3.tar.gz` | 146253 | `a5c7afd71a93a31ed74736f150108352fa49807ba422a6cfe911e48d2173b82b` |

[Original checksums](SHA256SUMS-0.1.0rc3-a0ac1bf.txt) and the [machine-readable record](candidate-0.1.0rc3.json)
retain every artifact member hash, runtime inventory and installation check.
The wheel contains 45 files; the source archive contains 55 regular files,
including both Python examples. All 39 runtime files match the build revision.
This preparation changes only the runtime version identifier, not protocol
bytes, cryptographic domains, trust rules or storage schemas. The candidate also
contains the previously merged corrections listed in the [notes](notes-0.1.0rc3.md).

## Reproduced packaging blocker

The main-branch source archive omitted `examples/transactions.py`. Requiring that
file in `tests/package_artifacts.py` rejected a fresh baseline archive with
`ValueError: package member inventory differs from the expected files`.
Adding its explicit inclusion to `MANIFEST.in` fixes the omission; inspection of
both new distributions passes. The inventory check now prevents recurrence.
No other runtime blocker was reproduced in this closeout.

## Executed validation

- macOS 15.6.1 arm64, Python 3.12.14: **1543 tests passed**, no skips or failures,
  in 113.95 seconds using source imports and a fresh locked rc3 environment.
  This includes generated/property tests, process-crash cases and transaction
  example regressions; generated cases are not additional pytest test counts.
- Ruff passed; strict mypy passed on 38 source files. uv 0.13.5 offline lock
  validation and dependency consistency passed. External locked versions did
  not change. Repository/link and traceability checks run again on the final
  documentation revision; their exact final totals belong to the PR result.
- Four bounded parser campaigns passed: seeds 20261110, 47,
  9007199254740991 and guided seed 20261112. Each ran 2000 mutations plus 25
  corpus cases, **8100 inputs total**. The guided run observed 169 Python edges,
  retained 33 inputs and found 8 novel-path mutations. These are run observations,
  not exhaustive protocol, HTTP, SQLite or native cryptographic fuzzing.
- **33 Mac installation checks** passed across base wheel, witness wheel and
  source-archive environments. Hashed locked runtime dependencies, CLI startup,
  dependency consistency, isolated imported-file hashes, witness smoke checks
  and public-only verification were checked. Both witness-capable environments
  completed the **21-check synthetic workflow** and transaction example help.
- **20 Linux installation checks** passed on the laptop, Linux x86_64/Python
  3.14.4, across witness-wheel and source-archive environments. Both completed
  the same 21-check workflow, witness/public checks, transaction help and all
  39 runtime hash comparisons. The exact files copied from Mac retained both
  artifact hashes. Only new isolated test directories were used; no service
  deployment or production keys were created.
- The transaction example's actual append/submit/error paths are exercised by
  the full suite. PR 72's separate cross-host transaction demonstration remains
  accepted evidence for its recorded revision, not a new rc3 cross-host run.
- Fresh PyPI and OSV queries completed for all 24 locked external packages and
  uv: **50 successful requests**, no listed advisories or yanked files. See the
  [dependency review](dependency-review-0.1.0rc3.md) for native-component scope.

An initial source-suite run used the older local environment: 1542 passed and
one inventory assertion failed because installed metadata said rc2 while source
said rc3. Installing the candidate in a fresh locked environment resolved that
mismatch; the complete suite then passed without changing or weakening tests.

## Commands and artifact provenance

The [build procedure](candidate-build.md) supplies the full environment setup.
The executed build used uv 0.13.5, build 1.6.1, Setuptools 84.2.1 and
`SOURCE_DATE_EPOCH=1794880031`. Paths below name isolated output environments;
substitute their absolute locations without changing revision or artifacts.

```sh
git archive a0ac1bfa61d3406c99b6bf758c62f6e840b633f3 | tar -x -C "$SOURCE"
uv sync --project "$SOURCE" --locked --no-editable --all-extras --all-groups --python "$PYTHON"
SOURCE_DATE_EPOCH=1794880031 "$SOURCE/.venv/bin/python" -m build --no-isolation "$SOURCE" --outdir "$DIST"
python tests/package_artifacts.py "$DIST" --output artifacts.json
PYTHONPATH=src "$SOURCE/.venv/bin/python" -m pytest tests/ -q
.venv/bin/ruff check src tests benchmarks examples
.venv/bin/mypy src
uv lock --check --offline
```

Installation checks exported hashed base/witness requirements with
`uv export --locked --no-default-groups --no-emit-project` (adding
`--extra witness` for witness environments), then used `uv venv`,
`uv pip install --require-hashes -r REQUIREMENTS`, and
`uv pip install --no-deps ARTIFACT`. Source-archive installs used
`--build-constraint` with `setuptools==84.2.1`. Each ran `uv pip check`.
Isolated Python ran `tests/wheel_smoke.py` (with `--witness` where installed),
`tests/public_fixture.py`, `tests/public_verify.py`,
`examples/verified_workflow.py OUTPUT`, and `examples/transactions.py --help`.
Mac imports were checked with `tests/validation_environment.py --import-mode wheel`;
Linux compared every installed runtime file directly against the committed export.

The required twelve-job CI matrix tests Python 3.12–3.14 on Ubuntu x86_64 and
macOS arm64 with locked and minimum-direct dependencies. Match the PR head,
tested merge revision and completed jobs before acceptance. Its builds are
separate artifacts, not validation of the exact local hashes by inference.

## Remaining acceptance

Review the PR and CI, then approve publication separately if desired. Refresh
advisories immediately before any approved publication; verify public downloads
and fresh installations afterward. P08 remains open until those steps finish.
If packaged inputs change, build new identified files and repeat installation
checks rather than reusing this approval or overwriting rc2.

The [research-demo operating rules](research-demo-closeout.md) are the agreed
scope. P05/P06 production provisioning and real-use acceptance remain partial.
P03 whole-machine power-loss testing is pending future validation; P04 independent
security review is pending independent evaluation. Both remain incomplete for
future production-readiness evaluation and neither blocks experimental research
publication. H1's primary research expectation remains unmet.

The later P03/P04 status clarification, including README wording, does not change
the recorded artifact bytes or validation results. Those files retain their
identified build revision. Including later packaged documentation in a candidate
requires a new build, hashes and installation checks before publication.
