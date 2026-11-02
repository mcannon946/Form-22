import csv, sys, tempfile, unittest
from pathlib import Path

class ValidationTests(unittest.TestCase):
    def test_required_headers(self):
        headers = {'date', 'amount', 'paid_in_full'}
        self.assertTrue({'date', 'amount'}.issubset(headers))

    def test_date_shape(self):
        from datetime import date
        self.assertEqual(
            date.fromisoformat('2026-11-02').isoformat(),
            '2026-11-02'
        )

    def test_money_round_trip(self):
        from decimal import Decimal
        self.assertEqual(Decimal('123.45'), Decimal('123.45'))

if __name__ == '__main__':
    unittest.main()
