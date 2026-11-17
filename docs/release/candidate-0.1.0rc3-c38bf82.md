# Refreshed experimental 0.1.0rc3 candidate

Prepared 17 November 2026 UTC from merged PR 74 revision
`c38bf821af013eaa4efa96a799577dab60250b48`. **Unpublished; review and separate
publication approval required.** No tag, release, deployment or PyPI upload was
created. Published rc2 assets are unchanged.

This refresh includes the accepted README wording: P03 is pending future
validation and P04 is pending independent evaluation. Both remain incomplete
future production-readiness evaluations and neither blocks experimental research
publication. Runtime code, examples, package version, dependency lock and build
recipe are unchanged from the earlier rc3 build. Only packaged README/derived
metadata and build timestamp differ; documentation evidence is updated separately.

## Exact review files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc3-py3-none-any.whl` | 109031 | `ef05e5ee702bc1fd7aa792e48c584afafcf6fb080cfd88c192c8d37807fdbbd3` |
| `casf-0.1.0rc3.tar.gz` | 146540 | `4a5343e5d63a29a3b9acc16ea3f0992154e868fe7a3064bda4aa34b7199c0de3` |

The [current checksums](SHA256SUMS-0.1.0rc3.txt) identify these new files. The
[machine-readable record](candidate-0.1.0rc3-c38bf82.json) retains member hashes,
build identity and installation results. Earlier rc3 files and
[their checksums](SHA256SUMS-0.1.0rc3-a0ac1bf.txt) remain historical review artifacts;
they have not been overwritten or approved for publication by this refresh.

## Build and package validation

A clean `git archive` export of the revision above was built in a new output
directory with uv 0.13.5, build 1.6.1 and Setuptools 84.2.1 on macOS arm64,
Python 3.12.14. `SOURCE_DATE_EPOCH=1794889130` identifies the build timestamp.
The [existing procedure](candidate-build.md) was reused without runtime changes.

```sh
git archive c38bf821af013eaa4efa96a799577dab60250b48 | tar -x -C "$SOURCE"
uv sync --project "$SOURCE" --locked --no-editable --all-extras --all-groups --python "$PYTHON"
SOURCE_DATE_EPOCH=1794889130 "$SOURCE/.venv/bin/python" -m build --no-isolation "$SOURCE" --outdir "$DIST"
python tests/package_artifacts.py "$DIST" --output artifacts.json
uv lock --check --offline
```

Inspection passed for 45 wheel members, 55 source-archive regular files and all
39 runtime files. The source archive's README equals the merged README bytes;
the wheel metadata includes its new pending-evaluation wording. New artifacts
were rehashed after installation, and earlier rc3 artifacts still match their
original hashes. Later evidence-document commits are not inputs to these files.

## Installation and advisory checks

All **33 Mac checks passed** across fresh base-wheel, witness-wheel and
source-archive environments. Hashed locked dependencies, dependency consistency,
CLI startup, isolated imports and runtime hashes, witness smoke checks and
public-only verification passed. Both witness-capable installs completed the
**21-check synthetic workflow** and transaction-example help.

Commands followed the existing procedure: `uv export --locked` with base/witness
requirements, `uv venv`, `uv pip install --require-hashes`, then
`uv pip install --no-deps ARTIFACT` and `uv pip check`. Source-archive installation
used the isolated backend constrained to `setuptools==84.2.1`. Tests ran with
`python -I` outside the checkout: `tests/validation_environment.py`,
`tests/wheel_smoke.py`, `tests/public_fixture.py`, `tests/public_verify.py`,
`examples/verified_workflow.py` and `examples/transactions.py --help`.
All private test material was synthetic; no production keys were provisioned.

Fresh [PyPI and OSV responses](dependency-review-0.1.0rc3-c38bf82.json) cover all
24 locked external packages plus uv 0.13.5. All **50 queries succeeded**, with
no listed vulnerabilities, pagination remainder or yanked files. The lock hash
and query time are retained. Dependency versions and license inventory are
unchanged. The [existing native-component scope](dependency-review-0.1.0rc3.md)
remains applicable; package queries do not certify host patches or native code.
Refresh advisories again immediately before approved publication if time passes.

## Linux and post-merge validation

All **20 Linux checks passed** in new isolated directories on the x86_64 laptop
with Python 3.14.4. The exact copied wheel and source archive retained the new
hashes above. Both witness-capable environments passed dependency consistency,
smoke/public verification, all 39 runtime hash comparisons, transaction-example
help and the **21-check synthetic workflow**. Existing services were not changed.

[Post-merge CI run 44016310435](https://github.com/hamdamme/casf/actions/runs/44016310435)
passed all **12 jobs** on the exact build revision `c38bf82`. Each job passed
**1543 tests** and the 21-check installed demo. This covers Python 3.12–3.14,
Ubuntu x86_64/macOS arm64, locked source and minimum-direct installed-wheel
configurations, including existing generated/fuzz/crash checks. CI built its own
artifacts; exact local-byte installation evidence is recorded separately above.
No redundant local full-suite run was used to stand in for that matrix.

Actual CI interpreters were 3.12.16/3.13.18/3.14.10 on Ubuntu and
3.12.10/3.13.17/3.14.10 on macOS. These are compatibility records, not claims of
host patch clearance. The machine-readable record retains each job's package
inventory, result line and source identity.

## Review boundary

Review these exact files with the [release notes](notes-0.1.0rc3.md). P08 remains
open until separately approved publication and public-download installation
verification. P05/P06 remain partial production gates. P03/P04 remain pending,
not completed. H1's primary research expectation remains unmet.
