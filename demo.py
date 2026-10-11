"""End-to-end demo: keys -> rotate -> log -> checkpoint -> export ->
verify -> tamper demonstrations. Run: python demo.py"""
import json, os, shutil
from auditfw import (HashChain, KeyRegistry, Signer, LogStorage,
                     seal_trail, verify_trail, AtRestEncryption,
                     CheckpointService, Verifier, TamperedError)

work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo")
shutil.rmtree(work, ignore_errors=True); os.makedirs(work)

reg = KeyRegistry(f"{work}/registry.json")
reg.generate("v1"); reg.rotate("v2")
signer = Signer(reg)

storage = LogStorage(f"{work}/audit.db")
chain = HashChain(storage)
hmac_key = os.urandom(32)

chain.append({"actor": "alice", "action": "login"}, signer, hmac_key, key_version="v1")
chain.append({"actor": "bob", "action": "pay", "amount": 100}, signer, hmac_key, key_version="v1")
reg.rotate("v3")
chain.append({"actor": "alice", "action": "logout"}, signer, hmac_key, key_version="v3")

trail = list(storage.iter_entries())
assert verify_trail(trail, hmac_key, seal_trail(trail, hmac_key))

reg.export_public_bundle(f"{work}/pubkeys.json")  # export AFTER all rotations
cp = CheckpointService(signer).create(storage)
json.dump(cp, open(f"{work}/checkpoint.json", "w"))
with open(f"{work}/events.jsonl", "w") as f:
    for e in trail: f.write(json.dumps(e) + "\n")

enc = AtRestEncryption()
blob = enc.encrypt_log(open(f"{work}/events.jsonl", "rb").read(), aad=b"audit")
assert enc.decrypt_log(blob, aad=b"audit") == open(f"{work}/events.jsonl", "rb").read()

pub = json.load(open(f"{work}/pubkeys.json"))
print("good log:", Verifier(pub, hmac_key).verify_file(f"{work}/events.jsonl"))
print("good log + cp:", Verifier(pub, hmac_key, cp).verify_file(f"{work}/events.jsonl"))

tampered = trail.copy(); tampered[1] = dict(tampered[1], payload={"actor": "mallory"})
bad_hmac = trail.copy(); bad_hmac[0] = dict(bad_hmac[0], hmac="00" * 32)
for name, entries_, v in [
    ("modification", tampered, Verifier(pub, hmac_key)),
    ("truncation",   trail[:-1], Verifier(pub, hmac_key, cp)),
    ("HMAC tamper",  bad_hmac,  Verifier(pub, hmac_key))]:
    try:
        v.verify_entries(entries_); print(name, ": NOT caught (bug!)")
    except TamperedError as e:
        print(f"{name} caught: {e}")
