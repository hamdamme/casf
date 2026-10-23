
"""Integrity verification CLI.

auditfw-verify --log events.jsonl --pubkeys pubkeys.json
               [--hmac-key KEY] [--checkpoint cp.json]
Exits 0 and prints OK if the chain is intact; reports the first
tampering point and exits 1 otherwise."""
import argparse, json, sys
from .verify import Verifier, TamperedError

def main(argv=None):
    ap = argparse.ArgumentParser(prog="auditfw-verify")
    ap.add_argument("--log", required=True)
    ap.add_argument("--pubkeys", required=True)
    ap.add_argument("--hmac-key", help="hex-encoded shared HMAC key")
    ap.add_argument("--checkpoint")
    a = ap.parse_args(argv)
    pub = json.load(open(a.pubkeys))
    cp = json.load(open(a.checkpoint)) if a.checkpoint else None
    v = Verifier(pub, bytes.fromhex(a.hmac_key) if a.hmac_key else None, cp)
    try:
        r = v.verify_file(a.log)
        print(f"OK: {r['entries']} entries verified, head={r['head_hash'][:16]}...")
        return 0
    except TamperedError as e:
        print(f"TAMPERED at entry seq={e.seq}: {e.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
