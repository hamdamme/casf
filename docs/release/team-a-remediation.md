# Team A audit remediation

Baseline: `e59fd64feed2d7136c0ee4ae543455ba90d3e572` (PR 57 merged).
Work was branched from freshly fetched `main`; the earlier CASF-01 local patch
was rechecked against that baseline. Prior PR 57 findings are not counted again.
The final source revision and hosted job results are recorded in the PR checks.
These changes remain unreleased.

## Findings and regression evidence

| Finding | Disposition | Regression identifiers |
| --- | --- | --- |
| CASF-01 | Fixed. Only actual Boolean policy values are accepted; invalid arguments raise ValueError before the core consumes records. Boolean suffix behavior and report assumptions are unchanged. | `test_allow_unwitnessed_rejects_non_booleans`, `test_bundle_rejects_non_boolean_unwitnessed_policy`, `test_anchored_policy_rejects_wrong_type_before_consuming_records`, `test_anchored_policy_preserves_boolean_suffix_behavior` |
| CASF-02 | Fixed. Permanent HTTP rejection, invalid receipt, trust failure and temporary unavailability have distinct documented categories. Exact pending bytes survive and can be retried. | `test_http_submission_categories`, `test_submission_preserves_error_categories`, `test_invalid_success_receipt_retains_pending`, `test_real_wrong_token_is_trust_failure_and_retry_succeeds` |
| CASF-H01 | Fixed. One shared origin validator rejects paths other than `/`, query delimiters and fragments before connection; no prefix-routing feature was added. | `test_base_url_components_rejected_before_connection`, `test_transport_valid_origin_and_timeout` |
| CASF-H02 | Fixed. Shared transport rejects Boolean/nonnumeric/nonfinite/nonpositive timeouts. Writer, typed handle, receipt recovery and reconciliation boundaries are checked. | `test_transport_invalid_timeout_rejected_before_connection`, `test_writer_timeout_boundaries`, `test_transport_valid_origin_and_timeout` |
| CASF-H03 | Targeted adversarial tests added for the confirmed boundary/error/redaction gaps. Existing trust, cleanup, concurrency and recovery tests remain in the full matrix. Expanded state machines and coverage-guided fuzzing are separate work, not implied by line coverage. | New audit/submission modules and existing online transport, receipt recovery, writer reconciliation and process-crash tests. |
| Additional redaction defects | Fixed. Online errors no longer echo arbitrary peer codes; receipt-schema messages and rendered exception chains do not echo peer field names. | `test_online_error_does_not_echo_peer_code`, `test_receipt_schema_traceback_does_not_echo_peer_fields`, malformed-receipt cases |

Tests live in [audit boundaries](../../tests/unit/test_audit_boundaries.py),
[submission categories](../../tests/unit/test_submission_categories.py),
[verifier](../../tests/unit/test_verifier.py) and
[bundle verification](../../tests/unit/test_verify_bundle.py).
The [requirement map](../../tests/requirement_evidence.json) links T16/T17/T18.

The original baseline runtime with the new tests produced **109 failures and
87 passes**. Failing cases: Boolean direct/wrapper policies 53; URL components
16; direct timeout types 3; writer timeout boundaries 17; HTTP categories 9;
propagated error categories 2; invalid receipt cases 6; real wrong-token CLI 1;
peer error-code redaction 1; receipt-schema traceback redaction 1. Existing valid/rejection controls passed and are
not claimed as newly failing regressions. A separate regression proved the
receipt-schema traceback leak before exception-chain suppression. Local before/
after JUnit and logs are retained with the validation outputs.

## Stable error policy and preserved behavior

[ADR-016](../adr/ADR-016-submission-error-categories.md) is the complete status /
exception / CLI exit table. 401/403 use the trust category (3); 409 uses the
new CasfError subclass EvidenceError (1); 400 and malformed receipt schemas
use SchemaError (2); 429/503 and network uncertainty remain InconclusiveError
(4); other unexpected statuses, including 500/502/504, are general errors (5).
Successful 200/201 responses still require authenticated receipts and a local
commit. Specific trust and schema errors are not collapsed into availability.

No canonicalization, digest/signature domain, key algorithm, signed schema,
trust predicate, verification precedence or transaction order was changed.
Existing CasfError handlers still catch the new subclass. Error diagnostics
omit peer payloads and synthetic token/key/passphrase/record markers. Rejected
submissions preserve canonical pending bytes; successful exact retries clear
the outbox. Existing lost-response receipt-recovery tests remain required.

## Validation procedure

Run from the repository root with the locked witness/dev/build dependencies.
Set `PYTHONPATH=src` only for source checks. Installed-wheel checks use an empty
PYTHONPATH and the separately installed interpreter. No audit helper directory
is added to either import path. Tool versions: uv 0.13.5, pip-audit 2.10.1,
coverage 7.13.4 (coverage instrumentation is separate from project dependencies).

```sh
uv sync --locked --extra witness --extra dev --group build
uv lock --check
uv pip check --python .venv/bin/python
.venv/bin/ruff check src tests benchmarks examples
.venv/bin/mypy src
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --hypothesis-show-statistics --junitxml=pytest.xml
PYTHONPATH=src .venv/bin/python -m coverage run --branch --source=src/casf -m pytest tests/ -q
.venv/bin/python -m coverage json -o coverage.json
.venv/bin/python tests/repository_check.py --output repository-check.json
git diff --check
uv build --python .venv/bin/python --no-build-isolation --out-dir dist
.venv/bin/python tests/package_artifacts.py dist --output package-artifacts.json
```

Each seed 20261110, 47 and 9007199254740991 runs
`PYTHONPATH=src .venv/bin/python -m tests.fuzz --seed SEED --cases 2000`.
Each campaign includes the 25-case corpus: 6,075 actual parser cases total.
Fresh wheel validation includes the full suite, import/file-hash guard,
`python -I tests/wheel_smoke.py --witness` and
`python -I examples/verified_workflow.py OUTPUT` (21 checks).

The existing CI workflow runs Ubuntu x86_64 and macOS arm64, Python
3.12/3.13/3.14, locked and minimum-direct dependencies: twelve jobs. Minimum
jobs test the installed wheel; locked jobs also build and exercise a fresh
installed wheel. Their environment/JUnit/fuzz artifacts identify actual patch
versions, dependency sets and executed cases. The PR carries final job status.

Fresh `pip-audit --disable-pip --no-deps -r audit-requirements.txt -s pypi`
and `-s osv` queries covered all 24 external packages exported directly from
the lockfile, including conditional packages: no known advisories were returned.
[Saved responses](team-a-advisories.json) bind the lockfile and query time.
Native libraries, vendor backports and host patches require deployment checks;
these query results do not establish their status.

## Required follow-up

The separate [production gates](production-readiness-gates.md) assign the type
of owner and evidence needed for physical power loss, independent security
assessment, persistent cross-host TLS, administrative separation, deployment/data
governance, research claims and a future release. Those are tracked work, not
silently accepted tests. No physical-power-loss or cross-host deployment claim
is made by hosted Linux jobs. Manual hardware testing must use disposable data
and a prepared recovery plan; no destructive test belongs on an everyday laptop
without an agreed test setup.

Canonical H1's unmet primary expectation remains visible. Expanded generated
state machines and coverage-guided fuzzing remain separately scoped. There is
no unresolved protocol-design change in this PR. The report records performed
checks; it is not a guarantee that every possible defect has been found.
