# Historical experiment provenance notes

This note explains the distinct commits recorded by the research artifacts.
It does not change any source result.

| Evidence | Recorded source revision | What the reference identifies |
|---|---|---|
| H1 rollback runs | `7fc4273a941845eac838a5f9fdcba5f2329c9c74` | Source commit recorded by the H1 harness |
| H3 outage runs | `1948a982cef52eabbf5cfdb3846d6e9b75ef7413` | Source commit recorded by the H3 harness |
| RQ4 collection | `7c388d385242238a40e572ed67e7e5fc9a1ab194` | Commit explicitly selected by the collector for its measured snapshot |
| Manuscript and research artifact set | `7c388d385242238a40e572ed67e7e5fc9a1ab194` | Repository revision cited by the preprint README when assembled |

The H1 raw environment records both the H1 source commit and separate SHA
256 values for the benchmark harness, dependency lock, and Python source tree.
Its captured working tree was dirty: `research/limitations.md` and
`research/protocol.md` were modified, and separate H3 and RQ2 files were
untracked. The recorded status did not list modified or untracked `src/casf`
files. The source tree digest was calculated from Python files under the
package directory, while the harness had its own digest. Thus the dirty
research state does not by itself show that H1 executed modified CASF code,
but the run was not captured from a clean full repository snapshot. Recreating
the exact run context requires matching the recorded package tree digest,
harness digest, lock digest, manifest, and environment; a checkout of the
commit alone is insufficient to recreate the whole dirty workspace.

The H1 raw files remain unchanged. The preprint artifact folder contains
sanitized copies that replace the absolute local module path with the
repository relative path. Its `SANITIZATION.md` records both original and
copy hashes. The replacement changes only that path string; it does not
replace or recompute a result.

Historical H1, H3, RQ4, and performance measurements remain applicable to
their recorded source snapshots and environments. The review candidate's
transport and parser changes do not retroactively change those observations.
Transport timing results are not measurements of the current candidate; any
new run is stored separately with new provenance.
