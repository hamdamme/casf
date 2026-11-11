# Published 0.1.0rc2 evidence

[CASF 0.1.0rc2](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2) is a
published GitHub prerelease for research and evaluation. Publication was explicitly
approved after PR 54 merged. No PyPI upload was performed.

The tag points to build commit `e92194fe0fa6eb37c2ff9016c381b8e734008880`.
Review documentation was accepted at `ecc47630c1340ac118dc50f2989cc51c37171080`.
These are different revisions: later documentation is not the package build source.
All 46 packaged source inputs were compared byte for byte with the source archive,
the build revision and the accepted review checkout. All 39 runtime files also
matched in the isolated public-download installations. Generated packaging metadata
is checked by the package inspector rather than treated as a tracked source input.
The subsequent handoff updates README release status; that documentation change
would alter metadata in a new build. It does not change the published assets.
The 46-input equality above refers to the accepted review revision, not a claim
that rebuilding a later documentation commit reproduces the released packages.

The [machine-readable record](publication-0.1.0rc2.json) contains exact hashes,
asset sizes, runtime inventories, validation totals and the reviewed CI run.
The release contains the retained wheel, source archive and `SHA256SUMS.txt`.
Automatic GitHub source snapshots are distinct from the inspected source archive;
use the explicitly named `casf-0.1.0rc2.tar.gz` asset.

## Executed checks

- Final PR 54 CI: twelve successful jobs, 1199 tests and the 21-check demo per job.
- Ubuntu 26.04.1 x86_64 laptop, Python 3.14.4: 1199 source tests and 1199 retained-wheel
  tests, with zero failures, errors or skips. Lint, typing, lock and package checks passed.
- Three seeded parser campaigns: 6000 mutations and 75 corpus replays passed.
- Source, retained wheel and retained source-archive demonstrations each completed 21 checks.
- After publication, unauthenticated downloads on Mac and Linux matched all three
  approved asset hashes. Fresh Linux installations of the downloaded wheel and source
  archive passed dependency consistency, imported-file verification, CLI startup,
  witness request/shutdown, public-only verification and 21 demonstration checks each.

The full test suites preceded publication; after publication the exact downloaded
bytes were checked and the listed installation workflows were rerun. They are not
represented as a second full-suite run against public downloads.

The original approval proposal and candidate records remain dated preparation
records, including their then-false approval fields. This publication record
supersedes those status fields without rewriting the historical evidence.
Release-note links resolve to the accepted review revision. Only preparation-status
wording changed when the approved notes became the published release body.

## Limits and maintenance

These results establish the tested experimental workflow, not production readiness,
an independent audit, physical power-loss durability or persistent cross-host service
operation. Runtime version strings do not establish distributor security backports.
The [native advisory assessment](dependency-review-0.1.0rc2.md) remains scoped.
Linux laptop validation is now performed; new WAN measurements, independently
operated witnesses and cloud deployment remain future work. Research H1's primary
expectation remains unmet. Historical research values are not release benchmarks.

Start with the [operating handoff](../operating-handoff.md). Any changed artifact
needs a new version and validation; never replace these published files in place.
