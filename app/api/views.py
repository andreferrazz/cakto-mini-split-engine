import hashlib
import json
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app.api.serializers import (
    PaymentInputSerializer,
    PaymentOutputSerializer,
    QuoteOutputSerializer,
)
from app.models import LedgerEntry, OutboxEvent, Payment
from app.services.split_calculator import calculate_platform_fee, calculate_splits


def _compute_payload_hash(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@api_view(["POST"])
def create_payment(request):
    serializer = PaymentInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return Response(
            {"detail": "Idempotency-Key header is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload_hash = _compute_payload_hash(request.data)

    # Check for existing payment with same idempotency key
    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.payload_hash != payload_hash:
            return Response(
                {"detail": "Idempotency-Key already used with a different payload."},
                status=status.HTTP_409_CONFLICT,
            )
        out = PaymentOutputSerializer(existing)
        return Response(out.data, status=status.HTTP_200_OK)

    gross = data["amount"]
    method = data["payment_method"]
    installments = data["installments"]

    fee = calculate_platform_fee(method, installments, gross)
    net = gross - fee
    split_results = calculate_splits(net, data["splits"])

    with transaction.atomic():
        payment = Payment.objects.create(
            gross_amount=gross,
            fee_amount=fee,
            net_amount=net,
            payment_method=method,
            installments=installments,
            currency=data["currency"],
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

        for s in split_results:
            LedgerEntry.objects.create(
                payment=payment,
                recipient_id=s["recipient_id"],
                role=s["role"],
                amount=s["amount"],
            )

        OutboxEvent.objects.create(
            event_type="payment.created",
            payload={
                "payment_id": str(payment.id),
                "gross_amount": str(payment.gross_amount),
                "fee_amount": str(payment.fee_amount),
                "net_amount": str(payment.net_amount),
                "payment_method": payment.payment_method,
                "installments": payment.installments,
                "splits": [
                    {
                        "recipient_id": s["recipient_id"],
                        "role": s["role"],
                        "amount": str(s["amount"]),
                    }
                    for s in split_results
                ],
            },
        )

    out = PaymentOutputSerializer(payment)
    return Response(out.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def checkout_quote(request):
    serializer = PaymentInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    gross = data["amount"]
    method = data["payment_method"]
    installments = data["installments"]

    fee = calculate_platform_fee(method, installments, gross)
    net = gross - fee
    split_results = calculate_splits(net, data["splits"])

    result = {
        "gross_amount": gross,
        "fee_amount": fee,
        "net_amount": net,
        "splits": split_results,
    }
    out = QuoteOutputSerializer(result)
    return Response(out.data)
