# Two-host TLS and recovery rehearsal

On 11 November 2026, the macOS control machine and dedicated Linux laptop passed
all 22 checks in [the machine-readable record](two-host-2026-11-11.json).
CASF runtime source was `cb3febff53a7cf8274a4b871f5be1382ebaedd33` on both hosts.
The new [helper](../../examples/two_host_rehearsal.py) changes no runtime protocol
or cryptographic implementation. The Linux baseline suite passed 1,409 tests in
86.86 seconds with locked dependencies on Python 3.14.4.

## Reproduce with synthetic data

Use Python without `-O` (the helper refuses optimized execution). Install the
repository's locked witness/dev dependencies with uv 0.13.5. Create a **new** private
fixture directory on the control machine:

```sh
PYTHONPATH=src .venv/bin/python examples/two_host_rehearsal.py prepare /ABSOLUTE/PRIVATE_ROOT --address TEST_LAN_IP
```

This creates encrypted synthetic authority/writer/witness keys, random bearer
credentials and short-lived private-CA certificate fixtures. Never upload this
directory or use its credentials for real records. Only the witness role directory
belongs on the Linux host. Keep the writer/authority roles on the control machine.
Copy the valid certificate/key to TEST_ROOT/tls.pem and TEST_ROOT/tls.key, mode 600.
Keep TEST_ROOT and role directories mode 700.

Install the identified Caddy binary only after verifying its recorded archive hash.
The [proxy example](two-host-proxy.example.json) is the tested configuration with
address/path placeholders; replace them before use. The backend binds loopback
8131, the TLS proxy binds the test LAN address on 8443. Admin/automatic HTTPS are
disabled. Full-duplex forwarding is required to return an early oversized-body
rejection without waiting for the rest of the upload. Read/header deadlines are
three seconds; backend body/header deadlines are two seconds. No system trust store
modification is required; the client trusts the fixture CA only during the run.

Create two **user** systemd units named `casf-rehearsal-witness.service` and
`casf-rehearsal-proxy.service`. Both use Type=simple, Restart=on-failure,
RestartSec=1, UMask=0077, NoNewPrivileges=true and TimeoutStopSec=15. Witness
WorkingDirectory is the checked-out repository and ExecStart is:

```text
/ABSOLUTE/REPO/.venv/bin/python examples/two_host_rehearsal.py serve /ABSOLUTE/TEST_ROOT/witness --port 8131
```

Proxy ExecStart is:

```text
/ABSOLUTE/TEST_ROOT/bin/caddy run --config /ABSOLUTE/TEST_ROOT/proxy.json
```

Start only these units. SSH must already authenticate the test host with a known
host key. The runner stops/restarts/kills only the named synthetic services, swaps
synthetic certificates/tokens, and ends by retaining revocation in the synthetic
writer. It never reboots or cuts power. Use a new fixture directory for each run;
preserve previous witness directories before replacing fixtures.

```sh
PYTHONPATH=src .venv/bin/python examples/two_host_rehearsal.py exercise /ABSOLUTE/PRIVATE_ROOT \
  --url https://TEST_LAN_IP:8443 --ssh-host TEST_USER@TEST_LAN_IP \
  --ssh-key /ABSOLUTE/SSH_KEY --remote-root /ABSOLUTE/TEST_ROOT \
  --output /ABSOLUTE/NEW_RESULTS
```

Checks are saved after each success; summary.json is written only after all checks
pass. Preserve unsuccessful runs too. The runner deliberately leaves the synthetic
services available for inspection; stop both named units when the rehearsal ends.
Do not publish private fixture directories or journals. The published result has
only public identifiers, hashes, platform descriptions and check outcomes.

## Corrections made while validating the harness

The first attempt reached eight passing checks before a proxy certificate-selection
error prevented the intended hostname validation. The next attempt reached the
request-size test but waited for an unread body. Explicit certificate selection
and full-duplex bounded proxy reads corrected those configurations. Failed attempts
were not counted as passes.

The fixture regression initially produced one failure and one pass because the CA
lacked strict-validation extensions. Added CA key usage and subject identifier,
and leaf authority identifier/basic constraints. Both fixture tests then passed;
`openssl verify -x509_strict -CAfile .../ca.pem .../valid.pem` returned OK. A fresh
complete rehearsal using those certificates passed 22/22 checks. The runtime CASF
trust model and signature domains were unchanged.

## Still required

This run used one administrator for both machines. It did not establish independent
administrative custody, restart after a machine reboot, physical power-loss recovery,
or production monitoring/backup operations. Follow the
[internal deployment acceptance plan](internal-deployment-acceptance.md) to close
each gate with its own evidence. No release was published.
