"""R07/R09/R10: follow-up read errors and configuration boundaries."""

import json
from types import SimpleNamespace

import pytest

from casf.canonical.jcs import canonicalize
from casf.cli import _load_trust, _writer, main
from casf.errors import NoCheckpointError, SchemaError, WitnessResponseError
from casf.online import fetch_latest
from casf.transport import request, validate_base_url
from tests.status import active_status
from tests.unit.test_checkpoint import _witness
from tests.unit.test_cli import _trust
from tests.unit.test_verify_online import _evidence
from tests.unit.test_writer import AUTH, LOG_ID, _manifest_envelope

INVALID_HOST_ORIGINS = [
    "https://[::1]suffix",
    "https://[v1.example]",
    "https://bad_host.example",
    "https://bad host",
    "https://bad\thost",
    "https://bad\nhost",
    "https://bad\rhost",
    "https://bad\x00host",
    "https://bad\x1fhost",
    "https://bad\x7fhost",
    "https://bad\x85host",
    "https://bad\u00a0host",
    " https://w.example",
    "\x01https://w.example",
    "https://w.example/\n",
    "https://bad\\host",
    "https://bad%20host",
    "https://bad..host",
    "https://-bad.example",
    "https://bad-.example",
    "https://" + "a" * 64 + ".example",
    "https://" + ".".join(["a" * 63] * 4),
]


@pytest.fixture
def bundle(tmp_path):
    witness = _witness(tmp_path)
    writer, mh, _, _ = _evidence(tmp_path, SimpleNamespace(witness=witness), records=2, witnessed=2)
    try:
        path = writer.export_bundle(LOG_ID, tmp_path / "bundle")
        (path / "status.jsonl").write_bytes(canonicalize(active_status(AUTH, mh)) + b"\n")
        yield path
    finally:
        writer.close()
        witness.close()


@pytest.mark.parametrize(
    "payload",
    [b"", b"<html>private-response</html>", b"{", b"[]", b'{"code":"NOT_FOUND"}', b'{"code":1}'],
)
def test_unrecognized_404_is_response_error(monkeypatch, payload):
    monkeypatch.setattr("casf.online.http_request", lambda *a, **k: (404, payload))
    with pytest.raises(WitnessResponseError, match="HTTP 404") as caught:
        fetch_latest("https://w.example", LOG_ID, "synthetic-token")
    assert "private-response" not in str(caught.value)


def test_no_checkpoint_keeps_explicit_category(monkeypatch):
    monkeypatch.setattr(
        "casf.online.http_request", lambda *a, **k: (404, b'{"code":"NO_CHECKPOINT"}')
    )
    with pytest.raises(NoCheckpointError):
        fetch_latest("https://w.example", LOG_ID, "synthetic-token")


@pytest.mark.parametrize(
    "status,payload,exit_code",
    [
        (404, b"", 5),
        (404, b"<html>private-response</html>", 5),
        (404, b'{"code":"NOT_FOUND"}', 5),
        (409, b"", 5),
        (409, b'{"code":"NO_CHECKPOINT"}', 5),
        (500, b"", 5),
        (404, b'{"code":"NO_CHECKPOINT"}', 4),
        (503, b"", 4),
        (429, b"", 4),
    ],
)
def test_online_cli_distinguishes_operational_errors(
    bundle, tmp_path, monkeypatch, capsys, status, payload, exit_code
):
    trust = _trust(tmp_path, _manifest_envelope(), mode="online", witness_url="https://w.example")
    state = tmp_path / "state.json"
    monkeypatch.setenv("CASF_WITNESS_TOKEN", "synthetic-token")
    monkeypatch.setattr("casf.online.http_request", lambda *a, **k: (status, payload))
    assert (
        main(
            [
                "verify",
                str(bundle),
                "--trust",
                str(trust),
                "--state",
                str(state),
                "--initialize-state",
                "--json",
            ]
        )
        == exit_code
    )
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["result"] == "INCONCLUSIVE"
    assert report["freshness_status"] == "INCONCLUSIVE"
    assert ("WITNESS_RESPONSE_ERROR" in report["diagnostic_codes"]) == (exit_code == 5)
    assert "WITNESS_STATE_CONFLICT" not in report["diagnostic_codes"]
    assert "private-response" not in output.out + output.err
    assert "synthetic-token" not in output.out + output.err
    # Independently authenticated status may advance, but a read failure never
    # advances the accepted checkpoint or invents a receipt.
    if state.exists():
        assert (
            json.loads(state.read_text())["manifests"][_manifest_envelope()["manifest_hash"]][
                "checkpoint"
            ]
            is None
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://w.example/prefix",
        "https://w.example?token=private",
        "https://w.example#",
    ],
)
def test_loaded_origin_is_validated(tmp_path, url):
    trust = _trust(tmp_path, _manifest_envelope(), witness_url=url)
    with pytest.raises(SchemaError, match="URL"):
        _load_trust(str(trust), LOG_ID)


@pytest.mark.parametrize(
    "mode,url,override",
    [
        ("online", "", None),
        ("integrity", "", "online"),
        ("anchored", "", "online"),
        ("online", "http://example.com", None),
        ("online", "https://w.example/prefix", None),
    ],
)
def test_invalid_online_origin_precedes_secrets_and_state(
    bundle, tmp_path, monkeypatch, capsys, mode, url, override
):
    trust = _trust(tmp_path, _manifest_envelope(), mode=mode, witness_url=url)
    state = tmp_path / "state.json"

    def forbidden(*a, **k):
        pytest.fail("invalid origin reached secrets or network")

    monkeypatch.setattr("casf.cli._secret", forbidden)
    monkeypatch.setattr("casf.online.http_request", forbidden)
    args = [
        "verify",
        str(bundle),
        "--trust",
        str(trust),
        "--state",
        str(state),
        "--initialize-state",
    ]
    if override:
        args += ["--mode", override]
    assert main(args) == 2
    assert "URL" in capsys.readouterr().err
    assert not state.exists() and not state.with_suffix(".json.lock").exists()


@pytest.mark.parametrize(
    "url,override",
    [
        ("", None),
        ("http://example.com", None),
        ("", "https://w.example/prefix"),
        ("https://w.example", ""),
    ],
)
def test_invalid_startup_origin_precedes_key_loading(tmp_path, monkeypatch, url, override):
    trust = _trust(tmp_path, _manifest_envelope(), witness_url=url)
    args = SimpleNamespace(
        local_only=False,
        trust=str(trust),
        status_file="unused",
        state="unused",
        initialize_state=False,
        url=override,
    )

    def forbidden(*a, **k):
        pytest.fail("invalid startup origin reached key loading")

    monkeypatch.setattr("casf.cli.load_key", forbidden)
    with pytest.raises(SchemaError):
        _writer(args, _manifest_envelope())


@pytest.mark.parametrize(
    "mode,url",
    [
        ("integrity", ""),
        ("anchored", ""),
        ("online", "https://w.example/"),
        ("online", "http://127.0.0.1:8123"),
        ("online", "http://[::1]:8123"),
    ],
)
def test_supported_origins_remain_valid(tmp_path, mode, url):
    trust = _trust(tmp_path, _manifest_envelope(), mode=mode, witness_url=url)
    assert _load_trust(str(trust), LOG_ID)[1]["witness_url"] == url


@pytest.mark.parametrize("url", INVALID_HOST_ORIGINS)
def test_malformed_origin_rejected_before_transport(url, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail("malformed origin reached transport or connection setup")

    monkeypatch.setattr("casf.online.http_request", forbidden)
    monkeypatch.setattr("casf.transport._connected_socket", forbidden)
    with pytest.raises(ValueError):
        request(url, "POST", "/", "synthetic-token", b"{}", timeout=1)
    with pytest.raises(SchemaError, match="URL"):
        fetch_latest(url, LOG_ID, "synthetic-token")


@pytest.mark.parametrize("url", INVALID_HOST_ORIGINS)
def test_malformed_origin_verification_has_no_side_effects(
    bundle, tmp_path, monkeypatch, capsys, url
):
    trust = _trust(tmp_path, _manifest_envelope(), mode="online", witness_url=url)
    state = tmp_path / "state.json"

    def forbidden(*a, **k):
        pytest.fail("malformed origin reached secrets, transport or state")

    monkeypatch.setattr("casf.cli._secret", forbidden)
    monkeypatch.setattr("casf.online.http_request", forbidden)
    monkeypatch.setattr("casf.cli.locked_state", forbidden)
    assert (
        main(
            [
                "verify",
                str(bundle),
                "--trust",
                str(trust),
                "--state",
                str(state),
                "--initialize-state",
                "--json",
            ]
        )
        == 2
    )
    assert "URL" in capsys.readouterr().err
    assert not state.exists() and not state.with_suffix(".json.lock").exists()


@pytest.mark.parametrize("url", INVALID_HOST_ORIGINS)
@pytest.mark.parametrize("override", [False, True])
def test_malformed_origin_startup_has_no_side_effects(tmp_path, monkeypatch, url, override):
    trust = _trust(
        tmp_path, _manifest_envelope(), witness_url="https://w.example" if override else url
    )
    state, database = tmp_path / "state.json", tmp_path / "writer.db"
    args = SimpleNamespace(
        local_only=False,
        trust=str(trust),
        status_file="unused",
        state=str(state),
        db=str(database),
        key="unused",
        passphrase_env="UNUSED",
        initialize_state=True,
        url=url if override else None,
    )

    def forbidden(*a, **k):
        pytest.fail("malformed origin reached secrets, transport or writer/state creation")

    monkeypatch.setattr("casf.cli._secret", forbidden)
    monkeypatch.setattr("casf.cli.load_key", forbidden)
    monkeypatch.setattr("casf.online.http_request", forbidden)
    monkeypatch.setattr("casf.writer.http_request", forbidden)
    monkeypatch.setattr("casf.cli.Writer.initialize_verified", forbidden)
    with pytest.raises(SchemaError, match="URL"):
        _writer(args, _manifest_envelope())
    assert not database.exists()
    assert not state.exists() and not state.with_suffix(".json.lock").exists()


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://w.example", ("w.example", 443, True)),
        ("HTTPS://W.EXAMPLE:8443/", ("w.example", 8443, True)),
        ("https://w.example.", ("w.example.", 443, True)),
        ("https://localhost", ("localhost", 443, True)),
        ("https://münich.example", ("münich.example", 443, True)),
        ("https://xn--mnich-kva.example", ("xn--mnich-kva.example", 443, True)),
        ("https://127.0.0.1", ("127.0.0.1", 443, True)),
        ("https://[2001:db8::1]:8443/", ("2001:db8::1", 8443, True)),
        ("https://[fe80::1%en0]", ("fe80::1%en0", 443, True)),
        ("https://" + "a" * 63, ("a" * 63, 443, True)),
        (
            "https://" + ".".join(["a" * 63] * 3 + ["a" * 61]) + ".",
            (".".join(["a" * 63] * 3 + ["a" * 61]) + ".", 443, True),
        ),
        ("http://127.0.0.1:8123/", ("127.0.0.1", 8123, False)),
        ("http://[::1]:8123", ("::1", 8123, False)),
    ],
)
def test_valid_hostname_compatibility(tmp_path, url, expected):
    assert validate_base_url(url) == expected
    trust = _trust(tmp_path, _manifest_envelope(), mode="online", witness_url=url)
    assert _load_trust(str(trust), LOG_ID)[1]["witness_url"] == url
