# Experimental release operating handoff

CASF 0.1.0rc2 is available as a [GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2).
Use it for research and evaluation. The [publication record](release/publication-0.1.0rc2.md)
identifies the exact source, assets, checks and limitations. There is no PyPI release.

## First use

1. Use a maintained Python 3.12–3.14 environment on a validated platform: Ubuntu
   x86_64 or macOS arm64. Review actual Python, SQLite and OpenSSL patch coverage.
2. Download the named wheel, named source archive and `SHA256SUMS.txt` from the
   release. Compare the checksum file with the [reviewed hashes](release/SHA256SUMS-0.1.0rc2.txt),
   then verify the downloaded packages. On Linux use `sha256sum -c SHA256SUMS.txt`;
   on macOS use `shasum -a 256 -c SHA256SUMS.txt`.
3. Follow [installation](installation.md) in a new virtual environment. Install the
   `witness` extra only when the reference HTTP witness is needed. The dependency
   lock documents the tested environment; package compatibility ranges are not a
   security recommendation for every version they permit.
4. Run the [21-check synthetic demonstration](demo.md) before handling real logs.
   It covers creation, retries, witnessing, verification, tampering, backup, restore,
   sealing and unavailable-witness behavior. Use a new output directory each time.
   Its keys and retained state are disposable test material, not operational identities.

## Operating responsibilities

| Responsibility | Required practice and guide |
| --- | --- |
| Authority and trust | Provision the authority, log and witness identities independently; distribute trusted pins and signed status through authenticated channels. See [administration](administration.md). |
| Retained state | Keep verifier/writer checkpoint and status state independently from evidence and witness backups. Initialize only an explicitly new observation. Never delete state to make rollback checks pass. |
| Writing and checkpointing | Use verified startup. Run one foreground [checkpoint worker](checkpoint-worker.md) per store under the application's supervisor. Append success means local commitment, not witnessed acceptance. Monitor backlog, retries and accepted receipts. |
| Witness service | The [reference server](witness-server.md) needs protected credentials, registration, HTTPS and resource limits for remote operation. A temporary loopback demonstration is not a persistent deployment. |
| Verification | Interpret integrity, anchored and online outcomes separately. An unavailable witness is inconclusive; supplied status is not proof of globally current revocation. See [verification](verification.md). |
| Backups | Use the supported SQLite backup operation, preserve trust/state/key material in their appropriate separate locations, and verify a restored copy before promotion. Do not copy only a live database file while ignoring its WAL. |
| Recovery | Preserve evidence, stop uncertain writes and follow [recovery drills](recovery-drills.md). Retry uncertain appends with the same event ID. Witness hashes cannot reconstruct lost records. |
| Witness rollback | Establish completeness against independently retained receipts before resuming signing; otherwise retire the witness identity. Client rollback detection is not automatic witness disaster recovery. |

## Maintenance checklist

Before each evaluation campaign:

- Record the package hashes, source revision, runtime/native components and configuration.
- Check available security updates and current advisories; assess relevant code paths and
  distributor backports. Preserve an existing tested environment before changing dependencies.
- Confirm available storage, working clock synchronization, protected keys, retained state
  and a recoverable backup. Inspect backlog and witness reachability when witnessed mode is used.

After a configuration, dependency or source change:

- Run the [locked checks](dependencies.md) and the relevant failure/recovery cases.
- Verify fresh installation and the demonstration; supported releases require the full
  [validation matrix](release/validation-matrix.md), not only one laptop's result.
- Document changed behavior and migration requirements. Test [store migration](storage-migrations.md)
  on copies and retain the original. Never bypass authentication to recover an old store.
- Keep results tied to their tested revisions; do not overwrite historical measurements.

Before any later release:

- Review advisories, licensing, package contents, support scope and claim boundaries.
- Build from identified committed source, retain exact hashes, obtain publication approval,
  and verify public downloads and installation afterward. Do not move an existing release tag
  or substitute new bytes under the same version.

For failures, preserve logs without secrets and stop at authentication, trust, corruption or
persistence errors. Follow the recovery guide rather than silently downgrading verification.
Report suspected vulnerabilities through [private reporting](https://github.com/hamdamme/casf/security/advisories/new),
using synthetic reproduction data. [SECURITY.md](../SECURITY.md) states best-effort response targets.

## What completion means

The experimental v0.1 release is published; the [tracker](release/completion-tracker.md)
separates delivered work from outstanding review. It does not establish a production
service or stable 1.0 contract. Persistent Linux/HTTPS operation, independently administered
witnesses, cloud deployment, physical power-loss testing and broader external review need
separate scope and acceptance. The research H1 primary expectation remains unmet.
No AWS server is needed merely to install, demonstrate or evaluate the published package.
