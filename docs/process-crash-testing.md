# Process crash and concurrency tests

The [process suite](../tests/process/) has 27 parameterized cases that kill
spawned Python workers with `SIGKILL`. Each worker announces a specific
transaction or file boundary through a pipe and blocks there. The parent
requires that announcement, sends the signal, joins the worker, and checks
its signal exit status before examining the stored data. A missed boundary,
timeout, unexpected exception or normal exit fails the test.

The suite uses real SQLite transactions, filesystem replacement and locks.
Test-only connection proxies and filesystem wrappers select the boundaries;
there are no production crash switches. Workers use `spawn`, avoiding inherited
SQLite connections. Competing workers announce their attempt to acquire the
real database or state-file lock; no sleep duration stands in for synchronization.

## Covered boundaries

| Operation | Kill location | Assertions after death and restart |
| --- | --- | --- |
| Append (3 cases) | Before insert; immediately before or after commit | Prior records survive; the interrupted append is absent or complete; the same event retries once, with identical committed bytes and contiguous sequences. |
| Checkpoint (4 cases) | Before/after commit, ordinary/final | Checkpoint, outbox and final seal commit together. Pending bytes survive; a committed final seal rejects new appends. |
| Competing append (4 cases) | Before/after another writer's commit, same/different event | The surviving process completes; retries preserve one event identity, committed bytes and a gap-free chain. |
| Witness acceptance (4 cases) | Before/after commit, ordinary/final | Head, checkpoint, receipt and record digests are all absent or committed. Identical retries replay the stored receipt; conflicting proposals do not move state. |
| Competing witness proposals (2 cases) | Before/after the first proposal's commit | A second process can commit only if the first proposal did not. The accepted branch remains the sole winner on subsequent retries. |
| Retained state (3 cases) | Before replacement; after replacement; after directory fsync | State is the complete old or new version at the selected boundary. Other manifests, private permissions, monotonic history and sticky revocation survive retry. |
| Retained-state contention (1 case) | After replacement while holding the sidecar lock | A waiting process acquires the released lock and sees the new state. The lock file retains its inode and revocation remains terminal. |
| Verified HTTP submission (6 cases) | After response; before/after local receipt commit, ordinary/final | The live witness replays the exact receipt with HTTP 200. Pending bytes and attempt count survive when uncommitted. Verified startup reconciles any missing receipt and external checkpoint, preserving records and final seals. |

The submission cases specifically exercise the interval where the independent
state file records an accepted checkpoint before the local receipt transaction
commits. A killed writer can therefore leave that file ahead of its database.
Restart uses independently supplied test pins, signed authority status and a
fresh witness response to recover the journal; it never clears retained state
to force progress.

## Running and reviewing

Install the locked development and witness dependencies, then run:

```bash
uv run --locked python -m pytest tests/process -v
uv run --locked python -m pytest tests -v --hypothesis-show-statistics
```

The ordinary CI suite includes these cases in all 12 Ubuntu/macOS jobs: CPython
3.12, 3.13 and 3.14 with locked and minimum direct dependencies. Read the exact
revision's job logs for pass/fail evidence. This document describes assertions,
not a permanent claim that a later revision has passed.

Existing unit tests separately cover interrupted backup, migration, export,
restore and journal reconciliation using selected process exits and injected
I/O failures. See [recovery drills](recovery-drills.md),
[storage migrations](storage-migrations.md),
[export behavior](export-and-reports.md), and the
[requirement evidence map](../tests/requirement_evidence.json).

## Limits

These are deterministic local-filesystem tests for macOS and Linux. Killing
a process leaves the operating system and its caches alive. In particular,
observing the new state after replacement but before directory fsync does not
establish persistence across power loss. The tests do not interrupt every
SQLite instruction, emulate torn sectors, reboot the host, or establish safety
on network filesystems. Hardware durability and witness disaster recovery
remain operational assumptions.

Death before state replacement can leave a private `.casf-state-*` temporary
file. Recovery reads the named state file, not that leftover. Do not promote
temporary files or remove them while a save could still be active.

All keys, events and credentials are synthetic. Sharing one test host does not
establish independent operational failure domains. Passing this matrix does
not by itself complete the [supported-platform review](release/validation-matrix.md)
or approve a release.
