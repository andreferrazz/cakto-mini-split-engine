# Mini Split Engine

API para cálculo de taxas de plataforma, split de recebíveis e persistência de pagamentos com ledger entries e outbox events.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Testes

```bash
python manage.py test app
```

## Endpoints

### POST /api/v1/payments

Cria um pagamento com cálculo de taxa, split de recebíveis, ledger entries e outbox event.

**Headers**: `Idempotency-Key` (obrigatório)

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-001" \
  -d '{
    "amount": "297.00",
    "currency": "BRL",
    "payment_method": "CARD",
    "installments": 3,
    "splits": [
      {"recipient_id": "p1", "role": "producer", "percent": "70"},
      {"recipient_id": "a1", "role": "affiliate", "percent": "30"}
    ]
  }'
```

### POST /api/v1/checkout/quote

Retorna o cálculo de taxa e split sem persistir.

```bash
curl -X POST http://localhost:8000/api/v1/checkout/quote \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100.00",
    "currency": "BRL",
    "payment_method": "PIX",
    "installments": 1,
    "splits": [
      {"recipient_id": "p1", "role": "producer", "percent": "100"}
    ]
  }'
```

## Tabela de Taxas

| Método | Parcelas | Taxa            |
|--------|----------|-----------------|
| PIX    | -        | 0%              |
| CARD   | 1x       | 3.99%           |
| CARD   | 2x       | 6.99%           |
| CARD   | 3x       | 8.99%           |
| CARD   | Nx       | 4.99 + 2*(N-1)% |
| CARD   | 12x      | 26.99%          |

## Decisões Técnicas

### Precisão monetária
Utilizo `Decimal` com `ROUND_HALF_UP` e `quantize("0.01")` para garantir precisão centesimal sem erros de ponto flutuante. Valores são trafegados como strings no JSON (`coerce_to_string=True`), prática padrão em APIs financeiras.

### Distribuição de remainder (centavos)
Calculo os valores de todos os recipients exceto o de maior percentual, e atribuo o restante (`net - soma_dos_outros`) ao maior. Isso garante por construção que `sum(splits) == net`, eliminando discrepâncias de arredondamento.

### Idempotência
O header `Idempotency-Key` é obrigatório. O payload é hashado com SHA-256 e armazenado junto ao pagamento. Na segunda chamada com mesma key:
- Mesmo payload → retorna o pagamento existente (200)
- Payload diferente → retorna conflito (409)

### Persistência transacional (Outbox Pattern)
Payment, LedgerEntries e OutboxEvent são criados dentro de `transaction.atomic()`. O evento fica com status `PENDING` até ser publicado por um worker externo (não implementado neste escopo). Isso garante consistência entre o estado do pagamento e os eventos emitidos.

### Métricas e observabilidade (próximos passos para produção)
- Instrumentar latência dos endpoints com Prometheus/Datadog
- Monitorar a fila de outbox events pendentes (alerta se crescer)
- Dashboard de volume de pagamentos por método e taxa média
- Tracing distribuído (OpenTelemetry) para debug de fluxos

### Próximos passos
- Worker para publicar outbox events (polling ou CDC)
- Autenticação e autorização (API keys, OAuth)
- Rate limiting
- Suporte a mais moedas
- Webhook de notificação para recipients

## Uso de IA

A documentação do projeto foi escrita com o auxilio do ChatGPT.
Parte dos testes foram escritos com o auxílio do GitHub Copilot.
