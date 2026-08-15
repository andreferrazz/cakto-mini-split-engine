# CLAUDE.md

## Project
Mini Split Engine — Django + DRF API for platform fee calculation, receivable splits, payment persistence with ledger entries, and transactional outbox events.

## Commands
- Run tests: `source .venv/bin/activate && python manage.py test app`
- Run server: `source .venv/bin/activate && python manage.py runserver`
- Migrations: `source .venv/bin/activate && python manage.py makemigrations && python manage.py migrate`

## Architecture
- `app/services/split_calculator.py` — Pure functions for fee and split calculation (no ORM)
- `app/api/views.py` — Function-based views with idempotency and atomic persistence
- `app/api/serializers.py` — Input validation and output formatting
- `app/models.py` — Payment, LedgerEntry, OutboxEvent
- `app/tests/` — Unit tests (split_calculator) and integration tests (API)

## Conventions
- Money: `Decimal` with `ROUND_HALF_UP`, `quantize("0.01")`
- JSON: Decimals as strings (`coerce_to_string=True`)
- Remainder cents go to the largest-share recipient
- Idempotency via SHA-256 hash of canonical JSON payload
- All persistence within `transaction.atomic()`
