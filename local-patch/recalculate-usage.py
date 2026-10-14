"""Separate API-price estimates, conditional purchased Credits and included-usage references."""
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


def calculate(row):
    model = row.get('pricingModel') or row.get('model')
    tier = row.get('pricingMode') or 'standard'
    if tier == 'default':
        tier = 'standard'
    total_input = max(0, int(row.get('input', 0)))
    cached = min(total_input, max(0, int(row.get('cached', 0))))
    tokens = [total_input - cached, cached, max(0, int(row.get('output', 0)))]
    result = {'model': model, 'tier': tier, 'tokens': tokens,
              'api_usd': None, 'purchased_credits': None, 'included_reference_units': None}
    api = TABLE['api'].get(model)
    if api:
        multiplier = Decimal(1) if tier == 'standard' else api.get('fast' if tier in ('fast', 'priority') else tier)
        if multiplier is not None:
            rates = api['long'] if total_input > api['threshold'] else api['short']
            result['api_usd'] = [Decimal(n) * Decimal(p) * Decimal(multiplier) / MILLION for n, p in zip(tokens, rates)]
    rates = TABLE['credits_per_million'].get(model)
    if rates:
        for output, weights in [('purchased_credits', 'purchased_credit_speed_multipliers'),
                                ('included_reference_units', 'included_speed_weights')]:
            multiplier = TABLE[weights].get(tier)
            if multiplier is not None:
                # Credit rates are flat: no API context threshold or cache-write charge.
                result[output] = [Decimal(n) * Decimal(p) * Decimal(multiplier) / MILLION for n, p in zip(tokens, rates)]
    return result


def build_report(rows, date):
    ledgers = {name: [Decimal(0), Decimal(0), Decimal(0)] for name in
               ('api_usd', 'purchased_credits', 'included_reference_units')}
    counts = {'uncached_input': 0, 'cached_input': 0, 'output': 0}
    missing = {name: set() for name in ledgers}
    by_tier = {}
    retained_rows = 0
    for row in rows:
        if row.get('day') != date:
            continue
        value = calculate(row)
        retained_rows += 1
        for key, number in zip(counts, value['tokens']):
            counts[key] += number
        group = by_tier.setdefault(value['tier'], {name: Decimal(0) for name in ledgers})
        for name in ledgers:
            if value[name] is None:
                missing[name].add(str(value['model']))
                continue
            for index, part in enumerate(value[name]):
                ledgers[name][index] += part
            group[name] += sum(value[name])
    output = {
        'date': date, 'captured_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'scope': 'retained native CodexBar usage rows; source report token count must be reconciled before treating rows as canonical',
        'raw_tokens': counts, 'total_tokens': sum(counts.values()), 'retained_rows': retained_rows,
        'billing_pool_for_each_request': 'not identified by these token rows',
        'actual_included_allowance_debit': None,
        'totals': {}, 'by_tier': by_tier,
        'limitations': TABLE['limitations'], 'official_sources': TABLE['sources'],
    }
    for name, parts in ledgers.items():
        output['totals'][name] = {
            **dict(zip(counts, parts)), 'total': sum(parts),
            'partial': bool(missing[name]), 'unpriced_models': sorted(missing[name]),
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    parser.add_argument('--database', type=Path, default=Path.home() / 'Library/Caches/CodexBar/cost-usage/cost-usage.sqlite')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    # An in-memory backup freezes one consistent dataset while the app continues scanning.
    snapshot = sqlite3.connect(':memory:')
    source.backup(snapshot)
    source.close()
    rows = (json.loads(payload) for (payload,) in snapshot.execute('SELECT payload FROM usage_rows'))
    report = build_report(rows, args.date)
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
