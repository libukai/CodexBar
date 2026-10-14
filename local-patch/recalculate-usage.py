"""Report recorded tokens by billing channel, model and requested speed."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import sqlite3

ROOT = Path(__file__).resolve().parent
MILLION = Decimal(1000000)
TABLE = json.loads((ROOT / 'official-pricing.json').read_text())
CHANNELS = ('unknown', 'chatgpt_subscription', 'purchased_credits', 'api')
TOKEN_KEYS = ('uncached_input', 'cached_input', 'output')


def calculate(row, channel='unknown'):
    if channel not in CHANNELS:
        raise ValueError('Unknown billing channel')
    model = row.get('pricingModel') or row.get('model')
    tier = row.get('pricingMode') or 'unknown'
    if tier == 'default':
        tier = 'standard'
    total_input = max(0, int(row.get('input', 0)))
    cached = min(total_input, max(0, int(row.get('cached', 0))))
    tokens = [total_input - cached, cached, max(0, int(row.get('output', 0)))]
    result = {'model': model, 'requested_tier': tier, 'tokens': dict(zip(TOKEN_KEYS, tokens)),
              'channel': channel, 'amount': None, 'unit': None, 'status': 'channel_unknown'}
    if channel == 'chatgpt_subscription':
        result['status'] = 'no_published_per_token_monetary_price'
        return result
    if channel == 'unknown':
        return result
    multiplier = None
    rates = None
    if channel == 'api':
        result['unit'] = 'USD'
        api = TABLE['api'].get(model)
        if api:
            multiplier = Decimal(1) if tier == 'standard' else api.get('fast' if tier in ('fast', 'priority') else tier)
            rates = api['long'] if total_input > api['threshold'] else api['short']
    elif channel == 'purchased_credits':
        result['unit'] = 'Credits'
        rates = TABLE['credits_per_million'].get(model)
        multiplier = TABLE['purchased_credit_speed_multipliers'].get(tier)
    result['status'] = 'price_or_tier_unknown'
    if rates is not None and multiplier is not None:
        result['amount'] = sum(Decimal(n) * Decimal(p) * Decimal(multiplier) / MILLION
                               for n, p in zip(tokens, rates))
        result['status'] = 'calculated_from_published_rates_not_invoice'
    return result


def build_report(rows, date, channel='unknown'):
    counts = dict.fromkeys(TOKEN_KEYS, 0)
    groups = {}
    retained_rows = 0
    for row in rows:
        if row.get('day') != date:
            continue
        value = calculate(row, channel)
        retained_rows += 1
        key = (value['channel'], value['model'], value['requested_tier'])
        group = groups.setdefault(key, {**value, 'tokens': dict.fromkeys(TOKEN_KEYS, 0),
                                        'total_tokens': 0, 'retained_rows': 0})
        group['retained_rows'] += 1
        for name, number in value['tokens'].items():
            counts[name] += number
            group['tokens'][name] += number
            group['total_tokens'] += number
        if group['retained_rows'] == 1:
            group['amount'] = value['amount']
        elif group['amount'] is not None and value['amount'] is not None:
            group['amount'] += value['amount']
        else:
            group['amount'] = None
    entries = list(groups.values())
    complete = bool(entries) and all(entry['amount'] is not None for entry in entries)
    return {
        'date': date, 'captured_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'scope': 'retained local CodexBar rows; reconcile with native report before treating as canonical',
        'channel': channel,
        'channel_basis': 'explicit user selection; not inferred from token rows' if channel != 'unknown' else 'unclassified',
        'tokens': counts, 'total_tokens': sum(counts.values()), 'retained_rows': retained_rows,
        'amount': sum(entry['amount'] for entry in entries) if complete else None,
        'unit': {'api': 'USD', 'purchased_credits': 'Credits'}.get(channel),
        'amount_complete': complete, 'by_model_and_requested_tier': entries,
        'limitations': TABLE['limitations'], 'official_sources': TABLE['sources'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    parser.add_argument('--channel', choices=CHANNELS, default='unknown',
                        help='Explicit billing source; token rows alone do not identify this.')
    parser.add_argument('--database', type=Path, default=Path.home() / 'Library/Caches/CodexBar/cost-usage/cost-usage.sqlite')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    snapshot = sqlite3.connect(':memory:')
    source.backup(snapshot)
    source.close()
    rows = (json.loads(payload) for (payload,) in snapshot.execute('SELECT payload FROM usage_rows'))
    report = build_report(rows, args.date, args.channel)
    snapshot.close()
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.parent.chmod(0o700)
        args.output.write_text(text)
        args.output.chmod(0o600)
        print(args.output)
    else:
        print(text)


if __name__ == '__main__':
    main()
