from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def calculate_platform_fee(method: str, installments: int, gross: Decimal) -> Decimal:
    """Calculate the platform fee based on payment method and installments."""
    if method == "PIX":
        rate = Decimal("0")
    elif installments == 1:
        rate = Decimal("3.99")
    else:
        rate = Decimal("4.99") + 2 * (installments - 1)

    fee = (gross * rate / 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return fee


def calculate_splits(net: Decimal, splits: list[dict]) -> list[dict]:
    """
    Distribute net amount among recipients according to their percentages.
    Remainder cents go to the largest-share recipient.
    """
    results = []
    largest_idx = 0
    largest_pct = Decimal("0")

    for i, s in enumerate(splits):
        pct = Decimal(str(s["percent"]))
        if pct > largest_pct:
            largest_pct = pct
            largest_idx = i
        results.append({
            "recipient_id": s["recipient_id"],
            "role": s["role"],
            "percent": pct,
            "amount": Decimal("0"),
        })

    # Calculate amounts for all non-largest recipients first
    allocated = Decimal("0")
    for i, r in enumerate(results):
        if i == largest_idx:
            continue
        amount = (net * r["percent"] / 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        r["amount"] = amount
        allocated += amount

    # Assign remainder to largest recipient
    results[largest_idx]["amount"] = net - allocated

    return results
