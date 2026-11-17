"""Synthetic transaction entry through the existing verified CASF CLI."""

import argparse
import json
import re
import tempfile
from pathlib import Path
from uuid import UUID

from casf.canonical.limits import SAFE_INT_MAX
from casf.cli import main as casf_main


def identifier(value):
    try:
        parsed = UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError('use a canonical UUID') from None
    if str(parsed) != value:
        raise argparse.ArgumentTypeError('use a canonical UUID')
    return value


def amount(value):
    if not re.fullmatch(r'0|[1-9][0-9]{0,15}', value):
        raise argparse.ArgumentTypeError('amount must be a nonnegative integer in minor units')
    result = int(value)
    if result > SAFE_INT_MAX:
        raise argparse.ArgumentTypeError('amount exceeds the safe integer limit')
    return result


def currency(value):
    if not re.fullmatch(r'[A-Z]{3}', value):
        raise argparse.ArgumentTypeError('currency must be three uppercase ASCII letters')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true', required=True,
                        help='acknowledge that this example is for synthetic records only')
    for name in ('db', 'key', 'trust', 'status-file', 'state'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--event-id', required=True, type=identifier,
                        help='reuse this UUID for retries of the same event')
    parser.add_argument('--transaction-id', required=True, type=identifier)
    parser.add_argument('--event', required=True, choices=('created', 'refunded', 'corrected'))
    parser.add_argument('--related-event-id', type=identifier)
    parser.add_argument('--amount-minor', required=True, type=amount)
    parser.add_argument('--currency', required=True, type=currency)
    parser.add_argument('--json', action='store_true', help='emit existing CLI JSON results')
    args = parser.parse_args(argv)
    if (args.event == 'created') != (args.related_event_id is None):
        parser.error('created must omit --related-event-id; refunds/corrections require it')
    if args.related_event_id == args.event_id:
        parser.error('an event cannot reference itself')
    payload = {'synthetic': True, 'transaction_id': args.transaction_id,
               'amount_minor': args.amount_minor, 'currency': args.currency}
    if args.related_event_id is not None:
        payload['related_event_id'] = args.related_event_id
    event = {'event_id': args.event_id, 'actor': 'synthetic-transaction-cli',
             'event_type': 'transaction-' + args.event, 'payload': payload, 'attributes': {}}
    common = ['--db', args.db, '--key', args.key, '--trust', args.trust,
              '--status-file', args.status_file, '--state', args.state]
    if args.json:
        common.append('--json')
    # TemporaryDirectory restricts access to the synthetic request. Never accept
    # local-only or initialize-state shortcuts through this application adapter.
    with tempfile.TemporaryDirectory(prefix='casf-transaction-') as temporary:
        path = Path(temporary) / 'event.json'
        path.write_text(json.dumps(event))
        code = casf_main(['append', *common, '--event', str(path)])
    if code:
        return code
    # Appending and witnessing are separate commits. On error, retry exactly
    # the same event ID and fields; the core owns durable pending recovery.
    code = casf_main(['checkpoint', *common])
    if code:
        return code
    return casf_main(['witness', 'work', *common, '--once'])


if __name__ == '__main__':
    raise SystemExit(main())
