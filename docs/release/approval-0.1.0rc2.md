# Proposed 0.1.0rc2 publication

Prepared for review only. Merging the release-evidence PR does not authorize
tag creation, asset upload, a GitHub release or package-index publication.

## Concrete proposal

- Destination: a GitHub **prerelease** in `hamdamme/casf`, titled `CASF 0.1.0rc2`.
- Proposed tag: `v0.1.0rc2`, pointing to build commit
  `e92194fe0fa6eb37c2ff9016c381b8e734008880`.
- That commit is already contained in merged history. It identifies the exact
  candidate source, not the later documentation/CI review commits. The notes
  and evidence live separately; do not point this tag at a newer commit while
  presenting these files as having been built from it.
- Assets: the two retained candidate files below and `SHA256SUMS.txt`.
- Release body: the reviewed [release notes](notes-0.1.0rc2.md), with relative
  documentation links converted to links at the accepted review revision.
- PyPI upload is excluded from this proposal. The name endpoint returned HTTP
  404 during review; that neither reserves the name nor establishes publishing
  permissions. No project, trusted publisher or credentials were configured.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc2-py3-none-any.whl` | 105223 | `c38dcfedfc7173db826177a96dc0d442e90f52bb04447c917395420e9233cec2` |
| `casf-0.1.0rc2.tar.gz` | 141119 | `62f9f829b43de8e4987aaed3393d7427bf4b137b197dc34fea4800c325dc16b1` |

The [machine-readable proposal](release-manifest-0.1.0rc2.json) and
[checksum file](SHA256SUMS-0.1.0rc2.txt) identify these bytes. The original
candidate approval record remains false; no later review silently grants
publication approval. Any changed file requires new hashes and validation.

## Review checklist

- [x] Exact artifact hashes, contents, build source and clean installation evidence recorded.
- [x] All packaged inputs still match the build revision; historical files preserved.
- [x] All 25 exact external package/tool advisory queries completed and license files inventoried.
- [x] Native-library findings assessed with explicit applicability and deployment limits.
- [x] Same candidate exercised on Python 3.12.16: 1199 tests and 21 workflow checks passed.
- [x] Candidate support policy and direct private-reporting route prepared; reporting setting confirmed enabled without sending a report.
- [x] Experimental scope, migration instructions, research limits and deferred deployment work stated in the notes.
- [ ] Proposed PR passes all twelve CI configurations at its final revision and is accepted.
- [ ] Immediately before publishing, refresh advisory/preflight checks, verify both retained file hashes and confirm that the proposed tag/release is absent.
- [ ] Obtain explicit approval of this destination, exact tag target, asset hashes, release notes and limitations.
- [ ] Only after approval, create the specified tag/prerelease and upload the exact retained files; do not substitute a rebuild.
- [ ] Download public assets, verify checksums and install them in a new environment; then record publication evidence and complete the handoff.

At preparation time GitHub listed no releases and private reporting was enabled.
No external security audit, production deployment or additional Linux/cloud
evaluation is implied by this proposal. Separate-runtime patching and operating
controls remain deployment responsibilities; the native review is not blanket
clearance of host libraries.

Release publication and final handoff remain open in the
[completion tracker](completion-tracker.md).
