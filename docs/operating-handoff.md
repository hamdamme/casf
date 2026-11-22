# Experimental release operating handoff

CASF 0.1.0rc3 is available as a [GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3).
Use it for research and evaluation. The [publication record](release/publication-0.1.0rc3.md)
identifies the exact source, assets, checks and limitations. There is no PyPI release.

The [replacement rc4 candidate](release/candidate-0.1.0rc4-d4721c4.md) includes
the C01–C06 fixes and C03/D01–D03 follow-up corrections absent from rc3.
It remains unpublished and now requires another build incorporating the SQLite
permissions and canonical JSONL corrections, followed by final review and approval.
The published rc3 evidence below is historical and does not validate rc4.

## First use

1. Use a maintained Python 3.12–3.14 environment on a validated platform: Ubuntu
   x86_64 or macOS arm64. Review actual Python, SQLite and OpenSSL patch coverage.
2. Download the named wheel, named source archive and `SHA256SUMS.txt` from the
   release. Compare the checksum file with the [reviewed hashes](release/SHA256SUMS-0.1.0rc3.txt),
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

The experimental rc2 release remains published and unchanged. The scoped PR 57
review was accepted at `e59fd64`; later changes carry their own tests and review
history, including PR 72's accepted synthetic transaction demonstration. See the
[research-demo closeout](release/research-demo-closeout.md) for current operating
rules and the [publication record](release/publication-0.1.0rc3.md) for rc3 verification.
The original review is not a claim that every later file was manually reviewed.
P05/P06 production provisioning and real-use acceptance remain incomplete; P08
is complete following approved rc3 publication and public-download verification.
P03 whole-machine power-loss testing is pending future validation; P04 independent
security review is pending independent evaluation. Both remain incomplete and
relevant to future production-readiness evaluation; neither blocks publication
of the experimental research release. Canonical H1's primary expectation remains
unmet. No AWS deployment or production keys are required for this research demo.
