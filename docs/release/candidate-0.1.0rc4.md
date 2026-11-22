# Experimental 0.1.0rc4 candidate

Prepared 18 November 2026 UTC (17 November in Chicago). **Unpublished; follow-up
review and separate publication approval pending.** No release/tag, PyPI upload,
service deployment or Zenodo deposit has been created. Published rc2/rc3 remain
unchanged and do not include the six PR 78 corrections.

## Follow-up maintenance

The November 21 follow-up requires corrections before publication. The historical
artifacts below do not contain these corrections and must not be approved as the
updated candidate. See [follow-up status](advisory-followup-2026-11-21.md).
A new build from reviewed source, exact checksums and installation evidence are
required after the fixes are accepted; retain the historical artifacts and records.

## Baseline and build identity

Baseline: PR 78 merge `dc0f47e87974e747f406e3e0e22bc581a367827f`.
Its [post-merge CI](https://github.com/hamdamme/casf/actions/runs/44207355025)
passed. No open PRs existed at preparation start. The previous remediation
[validation record](advisory-remediation-2026-11-17.md) retains 1606 source tests
and the earlier regression before/after evidence; those runs are not recounted
as new rc4 tests.

Exact build revision: `58e3db6f8ae8dbe362c2541be25fb486ab154128`. A clean `git archive`
export was built with uv 0.13.5, build 1.6.1, Setuptools 84.2.1 and
`SOURCE_DATE_EPOCH=1794963402`, Python 3.12.14 on macOS arm64.
Only version metadata, README and changelog/release notes changed after the
merged fixes. No additional protocol or behavior changes were made.
Later evidence-document commits are not inputs to these artifacts.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 110397 | `850de972d7e6bab4463ddc11f53fd950fc3cfad877c13496441577e7a4d70139` |
| `casf-0.1.0rc4.tar.gz` | 148027 | `daa4f9c6a56e31a8cd087ad36c00944af5a0111e03fe4f456b50875343f190b9` |

[Checksums](SHA256SUMS-0.1.0rc4.txt) and the [machine-readable record](candidate-0.1.0rc4.json)
retain exact member hashes, build identity and installation results.
Package inspection passed for 45 wheel members, 55 source-archive regular files
and all 39 runtime files. Neither artifact contains tests, full documentation,
research records, private keys or databases. The identified repository contains
the separate tests and documentation.

## Executed checks

Following the [build procedure](candidate-build.md), all **33 Mac installation
checks passed** in fresh base-wheel, witness-wheel and source-archive environments.
These include hashed locked dependencies, dependency consistency, CLI startup,
isolated imports and all runtime-file hashes, public-only verification, witness
smoke checks and transaction-example help. Both witness-capable installations
passed the **21-check synthetic workflow**. Artifacts were rehashed afterward.
No production records or keys were used.

Ruff, strict mypy (38 source files), uv 0.13.5 offline lock validation and
dependency consistency passed. External dependency versions are unchanged.
Focused advisory regressions and traceability checks passed: **69 tests** via
`PYTHONPATH=src python -m pytest tests/unit/test_advisory_c01_c06.py tests/unit/test_traceability.py -q`.
Repository/link checks and `git diff --check` passed; final totals are recorded
with the PR validation.
All **20 Linux checks passed** on the x86_64 laptop with Python 3.14.4,
in fresh wheel and source-archive environments. Both completed the 21-check
workflow, public-only verification, witness smoke tests, transaction help and
all 39 installed runtime-file hash comparisons. The exact copied files retained
the Mac checksums. Existing services and state were not changed. The
machine-readable record retains check results and actual native-component versions.

[CI run 44212436824](https://github.com/hamdamme/casf/actions/runs/44212436824)
passed all **10 jobs**, each with **1606 tests**, at PR head
`c9372e14678cc1721a245432787c634cbdbfc733`. This covers locked Linux/macOS Python
3.12–3.14 and minimum dependencies on Linux 3.12–3.14 and macOS 3.12, including
existing generated, crash, fuzz and package checks. CI builds its own packages;
exact local-byte installation evidence is recorded separately above.
Later evidence-only commits must pass their own PR checks before merge; this
run is not attributed to a later revision. Public-download installation checks
remain a publication step for this unpublished candidate.

Commands (absolute checkout/output paths substituted at execution):

```sh
git archive 58e3db6f8ae8dbe362c2541be25fb486ab154128 | tar -x -C "$SOURCE"
uv sync --project "$SOURCE" --locked --no-editable --all-extras --all-groups --python "$PYTHON"
SOURCE_DATE_EPOCH=1794963402 "$SOURCE/.venv/bin/python" -m build --no-isolation "$SOURCE" --outdir "$DIST"
python tests/package_artifacts.py "$DIST" --output artifacts.json
uv lock --check --offline
ruff check src tests benchmarks examples
mypy src
```

Installation used `uv export --locked --no-default-groups --no-emit-project`
(with `--extra witness` for witness environments), `uv venv`, hashed dependency
installation and `uv pip install --no-deps ARTIFACT`. The source-archive build
was constrained to `setuptools==84.2.1`. `uv pip check` passed in each environment.
Outside the checkout, `python -I` ran `tests/validation_environment.py`,
`tests/wheel_smoke.py`, `tests/public_fixture.py`, `tests/public_verify.py`, and,
for witness installs, `examples/verified_workflow.py` and transaction help.

## Dependency review

Fresh [PyPI/OSV results](dependency-review-0.1.0rc4.json) cover the 24 locked
external packages plus uv: **50 successful requests**, no listed vulnerabilities,
yanked files or pagination remainder. Query time, lock hash, exact versions and
response hashes are retained. This package-only review does not clear native
libraries or host patches. Existing [license and native-component scope](dependency-review-0.1.0rc3.md)
remains applicable; the new installation inventories record actual components.
Refresh advisory queries immediately before approved publication.

## Finite closeout checklist

1. Receive follow-up verification of C01–C06 against the named source revision.
   Assess additional findings separately; fix reproducible security, correctness
   or installation blockers within the experimental scope. Production features
   and unrelated enhancements remain future work.
2. If fixes are needed, retain regressions, commit them in a PR and obtain review
   and merge. Changed package inputs require newly identified builds and checks.
3. Review final CI, [release notes](notes-0.1.0rc4.md), exact hashes and fresh
   advisory results; obtain separate publication approval.
4. Publish the approved GitHub prerelease, verify downloads and fresh installs,
   update the advisory with the actual patched version and coordinate publication.
5. Create a new version of the existing Zenodo software record, verify downloaded
   bytes and DOI/citation, then record the experimental release closeout.

The current rc3 DOI and published assets must not be replaced. Reviewer feedback,
publication approval, public-download validation and Zenodo publication are still
pending. This release work does not close P03/P04/P05/P06 or change H1's recorded
research result. New maintenance findings after closeout are handled as separate
issues, not a claim that the completed release never existed.
