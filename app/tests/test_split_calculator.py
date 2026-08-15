from decimal import Decimal

from django.test import TestCase

from app.services.split_calculator import calculate_platform_fee, calculate_splits


class CalculatePlatformFeeTest(TestCase):
    def test_pix_zero_fee(self):
        fee = calculate_platform_fee("PIX", 1, Decimal("100.00"))
        self.assertEqual(fee, Decimal("0.00"))

    def test_card_1x_fee(self):
        fee = calculate_platform_fee("CARD", 1, Decimal("100.00"))
        self.assertEqual(fee, Decimal("3.99"))

    def test_card_3x_fee(self):
        # rate = 4.99 + 2*(3-1) = 8.99%
        fee = calculate_platform_fee("CARD", 3, Decimal("297.00"))
        self.assertEqual(fee, Decimal("26.70"))

    def test_card_12x_fee(self):
        # rate = 4.99 + 2*(12-1) = 26.99%
        fee = calculate_platform_fee("CARD", 12, Decimal("1000.00"))
        self.assertEqual(fee, Decimal("269.90"))


class CalculateSplitsTest(TestCase):
    def test_single_100_percent_split(self):
        splits = [{"recipient_id": "p1", "role": "producer", "percent": "100"}]
        result = calculate_splits(Decimal("100.00"), splits)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["amount"], Decimal("100.00"))

    def test_70_30_split(self):
        net = Decimal("270.30")  # 297 - 26.70
        splits = [
            {"recipient_id": "p1", "role": "producer", "percent": "70"},
            {"recipient_id": "a1", "role": "affiliate", "percent": "30"},
        ]
        result = calculate_splits(net, splits)
        total = sum(r["amount"] for r in result)
        self.assertEqual(total, net)

    def test_three_way_split_remainder(self):
        """3-way equal split on 100.00: 33.33 + 33.33 + 33.34 = 100.00"""
        net = Decimal("100.00")
        splits = [
            {"recipient_id": "r1", "role": "a", "percent": "33.34"},
            {"recipient_id": "r2", "role": "b", "percent": "33.33"},
            {"recipient_id": "r3", "role": "c", "percent": "33.33"},
        ]
        result = calculate_splits(net, splits)
        total = sum(r["amount"] for r in result)
        self.assertEqual(total, net)
