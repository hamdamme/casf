"""python -m tests.fuzz --seed 20261110 --cases 2000 --failures /tmp/casf-fuzz."""

import argparse
import json
from pathlib import Path

from tests.fuzz.runner import CampaignFailure, exercise, run_campaign


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20261110)
    parser.add_argument('--cases', type=int, default=2000)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--failures', type=Path, default=Path('fuzz-failures'))
    parser.add_argument('--replay', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.replay is not None:
            artifact = json.loads(args.replay.read_text())
            result = {'target': artifact['target'],
                      'outcome': exercise(artifact['target'], bytes.fromhex(artifact['data_hex']))}
        else:
            result = run_campaign(seed=args.seed, cases=args.cases,
                                  seconds=args.seconds, failures=args.failures)
    except CampaignFailure as exc:
        print(json.dumps({'result': 'FAIL', 'failure': exc.category, 'replay': str(exc.artifact)}))
        return 1
    except (TimeoutError, ValueError) as exc:
        print(json.dumps({'result': 'INCOMPLETE', 'error': type(exc).__name__}))
        return 2
    print(json.dumps({'result': 'PASS', **result}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
