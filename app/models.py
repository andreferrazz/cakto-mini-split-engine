import uuid

from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"

    class PaymentMethod(models.TextChoices):
        PIX = "PIX"
        CARD = "CARD"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    gross_amount = models.DecimalField(max_digits=15, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=15, decimal_places=2)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=4, choices=PaymentMethod.choices)
    installments = models.PositiveSmallIntegerField(default=1)
    currency = models.CharField(max_length=3, default="BRL")
    idempotency_key = models.CharField(max_length=255, unique=True)
    payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.gross_amount} {self.currency}"


class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="ledger_entries")
    recipient_id = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ledger {self.recipient_id}: {self.amount}"


class OutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PUBLISHED = "PUBLISHED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="outbox_events", null=True
    )
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Event {self.event_type} - {self.status}"
