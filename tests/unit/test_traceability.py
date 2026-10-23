"""R01 to R12 / T01 to T22 (SPEC §5, §26): traceability audit.

Every requirement and every mandatory test identifier in SPEC §5 and
§21 must be referenced by at least one test module, so the release
checklist can link each requirement to executed evidence. The audit
scans test sources; a gap fails the build instead of being papered
over in a document.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIREMENTS = {f"R{i:02d}" for i in range(1, 13)}
SPEC_TESTS = {f"T{i:02d}" for i in range(1, 23)}


def _references():
    text = ""
    for path in sorted((ROOT / "tests").rglob("*.py")):
        text += path.read_text()
    for path in sorted((ROOT / "vectors").rglob("*.json")):
        text += path.read_text()
    return set(re.findall(r"\b[RT]\d{2}\b", text))


def test_every_requirement_has_test_evidence():
    missing = sorted(REQUIREMENTS - _references())
    assert not missing, f"requirements without test evidence: {missing}"


def test_every_spec_test_is_covered():
    missing = sorted(SPEC_TESTS - _references())
    assert not missing, f"spec tests without coverage: {missing}"
