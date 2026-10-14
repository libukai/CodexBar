import importlib.util
from pathlib import Path
from decimal import Decimal
import unittest

spec = importlib.util.spec_from_file_location('pricing', Path(__file__).with_name('recalculate-usage.py'))
pricing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pricing)


class OfficialPricingTests(unittest.TestCase):
    def row(self, tier, input_tokens=1000000, cached=1000000, output=0):
        return pricing.calculate({'model': 'gpt-6.1-sol', 'pricingMode': tier,
                                  'input': input_tokens, 'cached': cached, 'output': output})

    def test_api_cache_uses_long_context_and_sixfold_ultrafast(self):
        self.assertEqual(sum(self.row('ultrafast')['api_usd']), Decimal('1.2'))

    def test_included_reference_uses_flat_cache_and_eightfold_weight(self):
        self.assertEqual(sum(self.row('ultrafast')['included_reference_units']), Decimal('20'))

    def test_purchased_credits_use_sixfold_weight(self):
        self.assertEqual(sum(self.row('ultrafast')['purchased_credits']), Decimal('15'))

    def test_fast_policies_are_separate(self):
        value = self.row('priority')
        self.assertEqual(sum(value['included_reference_units']), Decimal('6.25'))
        self.assertEqual(sum(value['purchased_credits']), Decimal('5'))

    def test_subscription_rate_does_not_jump_at_context_boundary(self):
        low = self.row('ultrafast', 272000, 272000)
        high = self.row('ultrafast', 272001, 272001)
        self.assertEqual(high['included_reference_units'][1] / low['included_reference_units'][1],
                         Decimal(272001) / Decimal(272000))
        self.assertGreater(high['api_usd'][1] / low['api_usd'][1], Decimal(2))

    def test_cache_is_subset_and_reasoning_is_not_charged_twice(self):
        row = {'model': 'gpt-6.1-sol', 'input': 100, 'cached': 80, 'output': 10,
               'reasoning': 7, 'pricingMode': 'standard'}
        value = pricing.calculate(row)
        self.assertEqual(value['tokens'], [20, 80, 10])
        self.assertEqual(sum(value['purchased_credits']), Decimal('0.0037'))

    def test_unknown_model_or_tier_does_not_invent_a_price(self):
        value = pricing.calculate({'model': 'unknown', 'pricingMode': 'ultrafast', 'input': 100})
        self.assertIsNone(value['api_usd'])
        self.assertIsNone(value['included_reference_units'])
        self.assertIsNone(self.row('unrecognized')['purchased_credits'])


if __name__ == '__main__':
    unittest.main()
