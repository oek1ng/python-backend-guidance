+++
schema_version = 1
id = "transactional-outbox"
title = "Record outbound events atomically with business changes"
description = "Write an outbox event in the same PostgreSQL transaction as the state change, then publish through a separate relay."
python = ">=3.12"
runtime = "sync"
tags = ["outbox", "dual-write", "event-publication", "atomicity"]
aliases = ["transactional outbox pattern", "database broker dual write"]
status = "draft"
example = "examples/transactional_outbox.py"
services = ["PostgreSQL >=16"]
libraries = {psycopg = ">=3.2,<4"}
[[sources]]
url = "https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html"
checked = 2026-11-16
+++

# Record outbound events atomically with business changes

## When to use

Use when a committed state change must eventually produce an event in another
system. Avoid a relay if the work is entirely local and needs no message.

## Rules

1. Insert a stable event ID and payload in the business transaction.
2. Have a separate relay publish committed rows and record delivery progress.
3. Mark delivery only after the transport's confirmation of acceptance.
4. Expect duplicate publication and make consumers idempotent.

## Reference example

Requires `accounts(id PRIMARY KEY, balance integer)` and
`outbox(id text PRIMARY KEY, payload jsonb NOT NULL)`.

```python
"""Persistence adapter: commit a business change and outbox event together."""

import json

from psycopg import Connection


def event_payload(account: int, amount: int) -> str:
    """Application event shape independent of transaction management."""
    return json.dumps({"account": account, "amount": amount})


def change_and_enqueue(
    connection: Connection[tuple[object, ...]], account: int, amount: int, event_id: str
) -> None:
    with connection.transaction():
        row = connection.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s RETURNING id",
            (amount, account),
        ).fetchone()
        if row is None:
            raise LookupError(account)
        _ = connection.execute(
            "INSERT INTO outbox (id, payload) VALUES (%s, %s)",
            (event_id, event_payload(account, amount)),
        )
```

## Guarantees and assumptions

On an idle autocommit connection the event and effect commit together or neither
does. This example covers the producer transaction. A relay, retries, retention,
ordering policy and lag monitoring are still required for eventual publication.

## Pitfalls

`commit(); publish()` can lose the notification after a crash. `publish(); commit()`
can expose an event for rolled-back state. An outbox gives no exactly-once broker
delivery, and deleting rows before publish confirmation loses events.

## Verification

Run `uv run pytest tests/integration/test_message_contracts.py --task transactional-outbox`.
Force an event insert failure and verify the business update rolled back.
Test relay crash windows separately when implementing that component.

## Sources

- [AWS transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
