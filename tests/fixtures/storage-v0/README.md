# Unversioned SQLite migration fixtures

`writer.sql` and `witness.sql` are SQLite dumps created with CASF revision
`444b999af54d41455b0c0ea1801734212283f35e`, before schema versioning. They use
only deterministic synthetic keys from `tests/unit/test_writer.py`.

The pair contains two records and two checkpoints. The writer has the first
receipt, a persisted timer, and a final pending checkpoint with three attempts
and a retry deadline. The witness has accepted both checkpoints, is sealed,
and retains active authority status. This models a lost final response.

Tests restore these exact dumps into SQLite and compare every row and BLOB
after migration. Another case drops only the later optional table to exercise
the earlier layout. A migrated pair must replay the original final receipt
and remain sealed. Do not regenerate these fixtures when the current schema
changes; retain them as the version 0 compatibility baseline.
