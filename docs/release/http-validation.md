# Witness transport validation

Date: 2026-10-24. Candidate based on commit
`3dd8d5c88bbdc0eb2f3fe8f90ab925517861aec3`, with the Uvicorn implementation
changes identified by the file hashes below. Requirements: R05, R06, R10,
and R12. This record is validation evidence, not release approval.

## Results

| Platform | Python | Full suite |
|---|---|---|
| macOS ARM | 3.12.11 | 236 passed |
| macOS ARM | 3.13.17 | 236 passed |
| macOS ARM | 3.14.9 | 236 passed |
| Linux ARM container | 3.12.15 | 236 passed |
| Linux ARM container | 3.13.17 | 236 passed |
| Linux ARM container | 3.14.9 | 236 passed |

The suite contains the original 213 tests and 23 new server checks. The
focused deadline test failed against the prior implementation because it
had no request_timeout configuration, then passed with the adapter.
The integrated checks also identified and resolved an ASGI interface
configuration error before final validation.

The Linux matrix passed lockfile checks, Ruff, mypy for 22 source files,
wheel and source archive builds, base wheel import and CLI startup, and
optional witness wheel request and shutdown checks. Wheel runtime dependencies
were installed from exports with hash verification. The base installation
was checked without Uvicorn; starting its witness reported the missing extra.
macOS lint and typing also passed.

The regression suite covers early body and authentication rejection, body
deadlines, real overload, body disconnects, cancellation while work continues,
active shutdown, malformed HTTP, JSON error sanitization, duplicate credentials,
chunked uploads without Content-Length, invalid settings, silent connection
bounds, and initial and subsequent header deadlines.

## Reproduction

Install the locked witness and development extras with uv 0.13.5 as described
in the [dependency guide](../dependencies.md), then run:

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/python -m pytest tests/
```

The [CI workflow](../../.github/workflows/ci.yml) records the build and fresh
wheel commands. The local Linux run used the same stages in disposable Python
slim containers. Image digests were:

| Python tag | Image digest |
|---|---|
| 3.12 | `sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704` |
| 3.13 | `sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962` |
| 3.14 | `sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8` |

## Validated file hashes

| File | SHA 256 |
|---|---|
| `src/casf/witness/http.py` | `8b08c061d7f0a8af5ea183d3ffcd845d647facf5bb6fbbb8236988a6cd926d6a` |
| `src/casf/witness/server.py` | `e36f8fd8bffc81e86cfddded570cff9fb44520c6882cc8ae969751b6018ebf0e` |
| `src/casf/witness/protocol.py` | `ec38f293eedbf3f58692a98c5a3ed4b76e405704f78b39eeacfee4dda6f4b560` |
| `tests/unit/test_witness_server.py` | `36e4260bd2f18cb35898cbf3d1bc2af9990e8fc14d522ffff1329a40cba51558` |
| `tests/wheel_smoke.py` | `c4371489d9d2e748715ce938c9643612c9cb64843a64ad99e54b13c1c685ebfa` |
| `uv.lock` | `91c0ca22aaab17b660ca15faf326d38313349eaa78ba866fcf81c9199dd6de0b` |

## Limits and outstanding acceptance

- Linux results are local ARM container runs. GitHub Actions and other
  architectures have not run this candidate yet.
- The existing Setuptools warning about license metadata remains. Package
  builds succeeded, but that separate release cleanup is still required.
- The added dependency review found no listed advisories for the queried
  versions; it does not establish security of the complete release.
- Wider deployment still requires HTTPS, proxy configuration, and independent
  witness administration. Availability under hostile traffic is not guaranteed.
- Shutdown deliberately waits for active witness work. A stalled filesystem
  can delay completion; no forced thread termination is used.
- No new performance measurements or independent security audit were performed.
- D05 remains open pending maintainer acceptance and remaining dependency and
  release reviews. This candidate has not been published as a release.

Original research results and local backups were preserved. All 119 protected
files matched their saved checksums or the documentation corrections already
committed with maintainer approval. No signed bytes, cryptographic primitives,
or witness state transition implementation changed.

## Subsequent status

The maintainer merged the implementation in PR 7 as `0f48046`.
[GitHub CI run 40123118085](https://github.com/hamdamme/casf/actions/runs/40123118085)
was subsequently verified as successful for Python 3.12, 3.13, and 3.14,
including builds and wheel checks. The earlier limitations above describe
the original local validation stage. The license warning was later corrected
and checked as recorded in the [dependency review](dependency-review.md).
Original validation results and file hashes above remain preserved.
