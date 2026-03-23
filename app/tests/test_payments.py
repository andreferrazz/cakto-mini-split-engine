from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from app.models import LedgerEntry, OutboxEvent, Payment


class CreatePaymentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/payments"

    def _make_payload(self, **overrides):
        data = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "CARD",
            "installments": 3,
            "splits": [
                {"recipient_id": "p1", "role": "producer", "percent": "70"},
                {"recipient_id": "a1", "role": "affiliate", "percent": "30"},
            ],
        }
        data.update(overrides)
        return data

    def test_pix_zero_fee_single_split(self):
        payload = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "PIX",
            "installments": 1,
            "splits": [
                {"recipient_id": "p1", "role": "producer", "percent": "100"},
            ],
        }
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="pix-001",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["fee_amount"], "0.00")
        self.assertEqual(resp.data["net_amount"], "100.00")
        self.assertEqual(len(resp.data["splits"]), 1)
        self.assertEqual(resp.data["splits"][0]["amount"], "100.00")

    def test_card_3x_70_30_split_sum_equals_net(self):
        payload = self._make_payload()
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="card-001",
        )
        self.assertEqual(resp.status_code, 201)
        net = Decimal(resp.data["net_amount"])
        split_sum = sum(Decimal(s["amount"]) for s in resp.data["splits"])
        self.assertEqual(split_sum, net)
        # fee = 8.99% of 297 = 26.70
        self.assertEqual(resp.data["fee_amount"], "26.70")

    def test_rounding_three_way_split(self):
        payload = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "PIX",
            "installments": 1,
            "splits": [
                {"recipient_id": "r1", "role": "a", "percent": "33.34"},
                {"recipient_id": "r2", "role": "b", "percent": "33.33"},
                {"recipient_id": "r3", "role": "c", "percent": "33.33"},
            ],
        }
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="round-001",
        )
        self.assertEqual(resp.status_code, 201)
        net = Decimal(resp.data["net_amount"])
        split_sum = sum(Decimal(s["amount"]) for s in resp.data["splits"])
        self.assertEqual(split_sum, net)

    def test_idempotency_same_payload_returns_200(self):
        payload = self._make_payload()
        resp1 = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="idem-001",
        )
        self.assertEqual(resp1.status_code, 201)

        resp2 = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="idem-001",
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp1.data["id"], resp2.data["id"])

    def test_idempotency_different_payload_returns_409(self):
        payload1 = self._make_payload()
        self.client.post(
            self.url, payload1, format="json",
            HTTP_IDEMPOTENCY_KEY="idem-002",
        )

        payload2 = self._make_payload(amount="500.00")
        resp = self.client.post(
            self.url, payload2, format="json",
            HTTP_IDEMPOTENCY_KEY="idem-002",
        )
        self.assertEqual(resp.status_code, 409)

    def test_missing_idempotency_key_returns_400(self):
        payload = self._make_payload()
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_pix_with_installments_returns_400(self):
        payload = self._make_payload(payment_method="PIX", installments=3)
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="val-001",
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_currency_returns_400(self):
        payload = self._make_payload(currency="USD")
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="val-002",
        )
        self.assertEqual(resp.status_code, 400)

    def test_splits_not_100_percent_returns_400(self):
        payload = self._make_payload(splits=[
            {"recipient_id": "p1", "role": "producer", "percent": "60"},
            {"recipient_id": "a1", "role": "affiliate", "percent": "30"},
        ])
        resp = self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="val-003",
        )
        self.assertEqual(resp.status_code, 400)

    def test_payment_creates_ledger_entries_and_outbox(self):
        payload = self._make_payload()
        self.client.post(
            self.url, payload, format="json",
            HTTP_IDEMPOTENCY_KEY="persist-001",
        )
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(LedgerEntry.objects.count(), 2)
        self.assertEqual(OutboxEvent.objects.count(), 1)
        event = OutboxEvent.objects.first()
        self.assertEqual(event.event_type, "payment.created")
        self.assertEqual(event.status, "PENDING")


class CheckoutQuoteAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/checkout/quote"

    def test_quote_returns_calculation_without_persisting(self):
        payload = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "CARD",
            "installments": 3,
            "splits": [
                {"recipient_id": "p1", "role": "producer", "percent": "70"},
                {"recipient_id": "a1", "role": "affiliate", "percent": "30"},
            ],
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["fee_amount"], "26.70")
        self.assertEqual(Payment.objects.count(), 0)
