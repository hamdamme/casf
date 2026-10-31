# CASF 0.1.0rc1 review candidate notes

These notes describe source changes prepared after the previously approved
0.1.0rc1 wheel and source archive. They are not approval or publication
instructions. The earlier artifacts and their recorded hashes remain
preserved as historical evidence and do not contain these changes.

## Changes under review

- Reject duplicate JSON properties and prohibited numeric forms in CLI,
  witness, writer response, and retained status state inputs.
- Apply a total deadline and response size limit to online verification and
  writer witness submission.
- Require the reference witness to hold a verified active status before it
  accepts checkpoints, and stop new acceptance after a verified revocation.
- Add local commands for signed manifests, verifier trust pins, signed status,
  witness registration, and linked epoch manifests.
- Include the `py.typed` package marker in built distributions.
- Permit export without a private key; append and checkpoint signing still
  require the log key.

The commands and bounds require full regression, lock, build, clean install,
and installed wheel checks before a new candidate can be approved.

## Artifact contents

The wheel contains the installable `casf` package, command entry point,
package metadata, license, and typing marker. The source archive contains the
package source and build metadata, README, license, and typing marker. Neither
artifact is expected to include the repository research tree, raw benchmark
results, RQ2 experiment files, reviewer material, local databases, or private
keys. These contents must be checked against the actual rebuilt artifacts.

## Verification workflow

Every CLI verification command requires `--state PATH`; first use also needs
`--initialize-state`. The exact examples are in
[installation and usage](../installation.md). Manifest, trust, status,
registration, and epoch setup are described in the
[administration guide](../administration.md).

The historical research measurements remain tied to their original code and
environment. The source changes listed here do not retroactively update those
measurements. The bounded network transport changes affect H3 timing, so a new
H3 run, if used, must have a separate result directory and provenance.

## Status

Not a built candidate. No artifact hashes are recorded here, and no release
has been published. Required checks and new maintainer approval remain
outstanding.
