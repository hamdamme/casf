"""Small, reproducible data profiles shared by generated-input tests."""

from hypothesis import settings
from hypothesis import strategies as st

from casf.canonical.limits import SAFE_INT_MAX, SAFE_INT_MIN

# Keep each generated tree small; boundary sizes have separate properties.
text = st.text(st.characters(blacklist_categories=('Cs',)), max_size=24)
integers = st.one_of(st.integers(SAFE_INT_MIN, SAFE_INT_MAX),
                     st.sampled_from([SAFE_INT_MIN, -1, 0, 1, SAFE_INT_MAX]))
values = st.recursive(st.none() | st.booleans() | integers | text,
                      lambda children: st.lists(children, max_size=4)
                      | st.dictionaries(text, children, max_size=4), max_leaves=16)
objects = st.dictionaries(text, values, max_size=4)

# Explicit settings apply on local and CI runs. No transient example database
# is needed for correctness: minimized findings become committed regressions.
profile = settings(max_examples=100, derandomize=True, database=None,
                   deadline=None, print_blob=True)
