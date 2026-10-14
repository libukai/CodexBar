import importlib.util
from pathlib import Path
from decimal import Decimal
import unittest

spec = importlib.util.spec_from_file_location('pricing', Path(__file__).with_name('recalculate-usage.py'))
pricing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pricing)


class OfficialPricingTests(unittest.TestCase):
    def row(self, channel, tier='ultrafast', input_tokens=1000000, cached=1000000, output=0):
        return pricing.calculate({'model': 'gpt-6.1-sol', 'pricingMode': tier,
                                  'input': input_tokens, 'cached': cached, 'output': output}, channel)

    def test_api_and_purchased_credits_have_their_own_units_and_prices(self):
        self.assertEqual(self.row('api')['amount'], Decimal('1.2'))
        self.assertEqual(self.row('purchased_credits')['amount'], Decimal('15'))
        self.assertEqual(self.row('api')['unit'], 'USD')
        self.assertEqual(self.row('purchased_credits')['unit'], 'Credits')

    def test_subscription_has_one_api_equivalent_total_not_a_separate_reference_index(self):
        value = self.row('chatgpt_subscription')
        self.assertEqual(value['amount'], Decimal('0.8'))
        self.assertEqual(value['unit'], 'USD_API_equivalent')
        self.assertNotIn('included_reference_units', value)
        self.assertEqual(value['status'], 'subscription_api_equivalent_not_invoice')

    def test_missing_channel_or_tier_does_not_assume_a_price(self):
        self.assertIsNone(pricing.calculate({'model': 'gpt-6.1-sol', 'input': 100})['amount'])
        self.assertIsNone(pricing.calculate({'model': 'gpt-6.1-sol', 'input': 100}, 'api')['amount'])
        self.assertIsNone(self.row('api', 'unrecognized')['amount'])

    def test_credits_do_not_jump_at_context_boundary(self):
        low = self.row('purchased_credits', input_tokens=272000, cached=272000)
        high = self.row('purchased_credits', input_tokens=272001, cached=272001)
        self.assertEqual(high['amount'] / low['amount'], Decimal(272001) / Decimal(272000))
        self.assertGreater(self.row('api', input_tokens=272001, cached=272001)['amount'] /
                           self.row('api', input_tokens=272000, cached=272000)['amount'], Decimal(2))

    def test_cache_subset_and_reasoning_not_counted_twice(self):
        value = pricing.calculate({'model': 'gpt-6.1-sol', 'input': 100, 'cached': 80,
                                   'output': 10, 'reasoning': 7, 'pricingMode': 'standard'}, 'purchased_credits')
        self.assertEqual(value['tokens'], {'uncached_input': 20, 'cached_input': 80, 'output': 10})
        self.assertEqual(value['amount'], Decimal('0.0037'))

    def test_report_groups_model_speed_and_never_sums_incomplete_money(self):
        rows = [{'day': '2026-10-14', 'model': model, 'pricingMode': tier, 'input': 100, 'output': 10}
                for model, tier in [('gpt-6.1-sol', 'standard'), ('unknown', 'ultrafast')]]
        result = pricing.build_report(rows, '2026-10-14', 'api')
        self.assertEqual(result['total_tokens'], 220)
        self.assertEqual(len(result['by_model_and_requested_tier']), 2)
        self.assertFalse(result['amount_complete'])
        self.assertIsNone(result['amount'])
        subscription = pricing.build_report(rows, '2026-10-14', 'chatgpt_subscription')
        self.assertIsNone(subscription['amount'])  # Unknown model keeps the total partial.
        self.assertEqual(subscription['total_tokens'], result['total_tokens'])


if __name__ == '__main__':
    unittest.main()
