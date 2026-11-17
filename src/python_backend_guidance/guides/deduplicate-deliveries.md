+++
schema_version = 1
id = "deduplicate-deliveries"
title = "Make message redelivery harmless with an atomic inbox"
description = "Commit a processed-message identity and its PostgreSQL effect in one transaction to suppress duplicate delivery effects."
python = ">=3.12"
runtime = "sync"
tags = ["inbox", "message-deduplication", "redelivery", "idempotent-consumer"]
aliases = ["duplicate message processing", "atomic inbox record"]
status = "draft"
example = "examples/deduplicate_deliveries.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://www.rabbitmq.com/docs/confirms"
checked = 2026-11-16
[[sources]]
url = "https://www.psycopg.org/psycopg3/docs/basic/transactions.html"
checked = 2026-11-16
+++

# Make message redelivery harmless with an atomic inbox

## When to use

Use for at-least-once delivery with a stable publisher-assigned message identity.
This local inbox protocol is broker-independent.

## Rules

1. Give each logical event a stable identity across redelivery.
2. Insert its inbox marker and apply its effect in the same transaction.
3. Acknowledge only after that transaction commits.
4. Scope IDs by producer/tenant where needed and retain them for the replay window.

## Reference example

Requires `inbox(id text PRIMARY KEY)` and `accounts(id PRIMARY KEY, balance integer)`.
Inputs are validated and authenticated before reaching this helper.

```python
"""Persistence adapter: commit an inbox record and local effect together."""

from psycopg import Connection


def apply_message(
    connection: Connection[tuple[object, ...]],
    message_id: str,
    account: int,
    amount: int,
) -> bool:
    with connection.transaction():
        inserted = connection.execute(
            "INSERT INTO inbox (id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
            (message_id,),
        ).fetchone()
        if inserted is None:
            return False
        if (
            connection.execute(
                "UPDATE accounts SET balance = balance + %s WHERE id = %s RETURNING id",
                (amount, account),
            ).fetchone()
            is None
        ):
            raise LookupError(account)
        return True
```

## Guarantees and assumptions

Use an idle autocommit connection. An effect failure rolls back the inbox marker.
The protocol assumes the publisher never assigns the same identity to different
payloads; add a payload fingerprint check if that guarantee is unavailable.

## Pitfalls

Marking processed before a separate effect transaction can lose the effect.
In-memory deduplication disappears on restart. An inbox cannot make an external
API call atomic with a database write.

## Verification

Run `uv run pytest tests/integration/test_message_contracts.py --task deduplicate-deliveries`.
Check duplicate delivery and rollback of the marker after an effect failure.

## Sources

- [RabbitMQ redelivery semantics](https://www.rabbitmq.com/docs/confirms)
- [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
