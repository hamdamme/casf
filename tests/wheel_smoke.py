"""Check base and optional witness installations using synthetic keys."""

import argparse
import http.client
import importlib.util
import json
import tempfile
import threading
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf.errors import CasfError
from casf.witness.http import WitnessService, make_server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", action="store_true")
    args = parser.parse_args()
    package_init = Path(__import__("casf").__file__).resolve()
    assert package_init.with_name("py.typed").is_file()
    with tempfile.TemporaryDirectory() as directory:
        service = WitnessService(Path(directory) / "smoke.db",
                                 Ed25519PrivateKey.from_private_bytes(b"s" * 32),
                                 token="synthetic-wheel-token")
        try:
            if not args.witness:
                assert importlib.util.find_spec("uvicorn") is None
                try:
                    make_server(service, "127.0.0.1", 0)
                except CasfError as exc:
                    assert "casf[witness]" in str(exc)
                else:
                    raise AssertionError("base install unexpectedly started a server")
                print("Base wheel import and optional dependency error passed")
                return
            server = make_server(service, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            connection = http.client.HTTPConnection(*server.server_address, timeout=5)
            try:
                connection.request("GET", "/unknown", headers={
                    "Authorization": "Bearer synthetic-wheel-token"})
                response = connection.getresponse()
                assert response.status == 404
                assert json.loads(response.read())["code"] == "NOT_FOUND"
            finally:
                connection.close()
                server.shutdown()
                thread.join(5)
                server.server_close()
            assert not thread.is_alive()
            print("Witness wheel request and shutdown passed")
        finally:
            service.close()


if __name__ == "__main__":
    main()
