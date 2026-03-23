from decimal import Decimal

from rest_framework import serializers


class SplitInputSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=255)
    role = serializers.CharField(max_length=50)
    percent = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=True)


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    currency = serializers.CharField(max_length=3)
    payment_method = serializers.ChoiceField(choices=["PIX", "CARD"])
    installments = serializers.IntegerField(default=1)
    splits = SplitInputSerializer(many=True)

    def validate_currency(self, value):
        if value != "BRL":
            raise serializers.ValidationError("Only BRL currency is supported.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_installments(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError("Installments must be between 1 and 12.")
        return value

    def validate_splits(self, value):
        if len(value) < 1 or len(value) > 5:
            raise serializers.ValidationError("Must have between 1 and 5 splits.")
        return value

    def validate(self, data):
        method = data.get("payment_method")
        installments = data.get("installments", 1)

        if method == "PIX" and installments != 1:
            raise serializers.ValidationError(
                {"installments": "PIX payments do not support installments."}
            )

        splits = data.get("splits", [])
        total_pct = sum(Decimal(str(s["percent"])) for s in splits)
        if total_pct != Decimal("100"):
            raise serializers.ValidationError(
                {"splits": "Split percentages must sum to exactly 100."}
            )

        return data


class LedgerEntryOutputSerializer(serializers.Serializer):
    recipient_id = serializers.CharField()
    role = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)


class PaymentOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    gross_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    fee_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    net_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    payment_method = serializers.CharField()
    installments = serializers.IntegerField()
    currency = serializers.CharField()
    splits = LedgerEntryOutputSerializer(many=True, source="ledger_entries")
    created_at = serializers.DateTimeField()


class QuoteOutputSerializer(serializers.Serializer):
    gross_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    fee_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    net_amount = serializers.DecimalField(max_digits=15, decimal_places=2, coerce_to_string=True)
    splits = LedgerEntryOutputSerializer(many=True)
