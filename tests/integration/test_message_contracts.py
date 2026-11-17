from typing import Never

import psycopg
import pytest

from examples.quarantine_poison_messages import Envelope
from tests.contracts import (
    ApplyMessage,
    Broker,
    ChangeAndEnqueue,
    Connect,
    ConsumeJSON,
    Database,
    ProcessDelivery,
)


@pytest.mark.contract("ack-after-commit")
class TestAcknowledgement:
    def test_commit_failure_leaves_delivery_unacknowledged(
        self, implementation: ProcessDelivery, pg: Database, broker: Broker
    ) -> None:
        connection, channel, queue = broker
        _ = pg.execute("CREATE TABLE permitted (id text PRIMARY KEY)")
        _ = pg.execute(
            "CREATE TABLE effects (id text PRIMARY KEY REFERENCES permitted(id) "
            "DEFERRABLE INITIALLY DEFERRED)"
        )
        channel.basic_publish("", queue, b"bad")
        delivery, _, _ = channel.basic_get(queue)
        assert delivery is not None

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            implementation(channel, delivery.delivery_tag, pg, "bad")
        channel.close()
        new_channel = connection.channel()
        redelivery, _, body = new_channel.basic_get(queue)
        assert redelivery is not None
        assert body == b"bad"
        new_channel.basic_ack(redelivery.delivery_tag)

    def test_committed_effect_is_acknowledged(
        self,
        implementation: ProcessDelivery,
        pg: Database,
        pg_connect: Connect,
        broker: Broker,
    ) -> None:
        connection, channel, queue = broker
        _ = pg.execute("CREATE TABLE effects (id text PRIMARY KEY)")
        channel.basic_publish("", queue, b"good")
        delivery, _, _ = channel.basic_get(queue)
        assert delivery is not None

        implementation(channel, delivery.delivery_tag, pg, "good")

        assert pg_connect().execute("SELECT id FROM effects").fetchall() == [("good",)]
        # Unacked deliveries are invisible on basic_get until their channel closes.
        channel.close()
        assert connection.channel().basic_get(queue)[0] is None


@pytest.mark.contract("deduplicate-deliveries")
class TestInbox:
    def test_redelivery_has_one_local_effect(
        self, implementation: ApplyMessage, accounts: Database
    ) -> None:
        _ = accounts.execute("CREATE TABLE inbox (id text PRIMARY KEY)")

        assert implementation(accounts, "message", 1, 10) is True
        assert implementation(accounts, "message", 1, 10) is False
        assert accounts.execute(
            "SELECT balance FROM accounts WHERE id=1"
        ).fetchone() == (110,)

    def test_failed_effect_does_not_mark_message_processed(
        self, implementation: ApplyMessage, accounts: Database
    ) -> None:
        _ = accounts.execute("CREATE TABLE inbox (id text PRIMARY KEY)")

        with pytest.raises(LookupError):
            _ = implementation(accounts, "message", 99, 10)
        assert accounts.execute("SELECT count(*) FROM inbox").fetchone() == (0,)


@pytest.mark.contract("transactional-outbox")
class TestOutbox:
    def test_failed_outbox_insert_rolls_back_business_change(
        self, implementation: ChangeAndEnqueue, accounts: Database
    ) -> None:
        _ = accounts.execute("CREATE TABLE outbox (id text PRIMARY KEY, payload jsonb)")
        _ = accounts.execute("INSERT INTO outbox VALUES ('event', '{}')")

        with pytest.raises(psycopg.errors.UniqueViolation):
            implementation(accounts, 1, 10, "event")
        assert accounts.execute(
            "SELECT balance FROM accounts WHERE id=1"
        ).fetchone() == (100,)

    def test_change_and_event_commit_together(
        self, implementation: ChangeAndEnqueue, accounts: Database, pg_connect: Connect
    ) -> None:
        _ = accounts.execute("CREATE TABLE outbox (id text PRIMARY KEY, payload jsonb)")

        implementation(accounts, 1, 10, "event")

        observer = pg_connect()
        assert observer.execute("SELECT payload FROM outbox").fetchone() == (
            {"account": 1, "amount": 10},
        )
        assert observer.execute(
            "SELECT balance FROM accounts WHERE id=1"
        ).fetchone() == (110,)


@pytest.mark.contract("quarantine-poison-messages")
class TestPoisonMessages:
    def test_invalid_message_reaches_dead_letter_queue(
        self, implementation: ConsumeJSON, broker: Broker
    ) -> None:
        _, channel, dead = broker
        source = channel.queue_declare(
            queue="",
            exclusive=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dead},
        ).method.queue
        channel.basic_publish("", source, b"not-json")
        delivery, _, body = channel.basic_get(source)
        assert delivery is not None and body is not None
        calls: list[Envelope] = []

        assert (
            implementation(channel, delivery.delivery_tag, body, calls.append) is False
        )
        # queue_declare is a broker round trip after the rejection.
        _ = channel.queue_declare(queue=source, passive=True)
        moved, _, body = channel.basic_get(dead)
        assert moved is not None
        assert body == b"not-json"
        assert calls == []
        channel.basic_ack(moved.delivery_tag)

    def test_handler_failure_remains_unacknowledged(
        self, implementation: ConsumeJSON, broker: Broker
    ) -> None:
        connection, channel, queue = broker
        channel.basic_publish("", queue, b'{"id":"1"}')
        delivery, _, body = channel.basic_get(queue)
        assert delivery is not None and body is not None

        def fail(message: Envelope) -> Never:
            raise OSError("temporary")

        with pytest.raises(OSError):
            _ = implementation(channel, delivery.delivery_tag, body, fail)
        channel.close()
        replacement = connection.channel()
        assert replacement.basic_get(queue, auto_ack=True)[0] is not None
