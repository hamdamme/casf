
"""Versioned key registry. Rotation never invalidates historical records:
verifiers resolve the public key by entry['key_version']."""
import json, os, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

class KeyRegistry:
    def __init__(self, path: str):
        self.path = path
        self._data = json.load(open(path)) if os.path.exists(path) else {
            "keys": {}, "active": None}

    def generate(self, version: str, activate: bool = True) -> None:
        priv = Ed25519PrivateKey.generate()
        self._data["keys"][version] = {
            "created_at": int(time.time()),
            "private": priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()).decode(),
            "public": priv.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
        }
        if activate:
            self._data["active"] = version
        self._save()

    def rotate(self, new_version: str) -> None:
        """Old keys stay in the registry so historical signatures verify."""
        self.generate(new_version, activate=True)

    def private_key(self, version: str = None):
        v = version or self._data["active"]
        pem = self._data["keys"][v]["private"].encode()
        return serialization.load_pem_private_key(pem, password=None)

    def public_key_pem(self, version: str) -> str:
        return self._data["keys"][version]["public"]

    def active_version(self) -> str:
        return self._data["active"]

    def export_public_bundle(self, out_path: str) -> None:
        """Out-of-band distribution: verifiers never read the registry."""
        json.dump({v: k["public"] for v, k in self._data["keys"].items()},
                  open(out_path, "w"), indent=2)

    def _save(self):
        json.dump(self._data, open(self.path, "w"), indent=2)

class Signer:
    def __init__(self, registry: KeyRegistry):
        self.registry = registry

    def sign(self, data: bytes, version: str = None) -> bytes:
        v = version or self.registry.active_version()
        return self.registry.private_key(v).sign(data)

    def active_version(self) -> str:
        return self.registry.active_version()
