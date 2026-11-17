import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import LiteralString, Never

import psycopg
import pytest

from tests.contracts import (
    Connect,
    CreateReservations,
    CreditOnce,
    Database,
    ExpandProfile,
    ExplainLookup,
    FencedWrite,
    FindUser,
    LoadItems,
    OpenPool,
    OwnedDocument,
    Page,
    ProfileModule,
    RunMigration,
    RunTransaction,
    TenantDocument,
    Transfer,
    UpdateDocument,
)


@pytest.mark.contract("deduplicate-mutations")
class TestMutationDeduplication:
    @pytest.fixture
    def database(self, accounts: Database) -> Database:
        _ = accounts.execute(
            "CREATE TABLE requests (key text PRIMARY KEY, account bigint NOT NULL, "
            "amount integer NOT NULL, result integer)"
        )
        return accounts

    def test_repeated_mutation_returns_original_result(
        self, implementation: CreditOnce, database: Database, pg_connect: Connect
    ) -> None:
        assert implementation(database, "key", 1, 10) == 110
        observer = pg_connect()
        assert implementation(observer, "key", 1, 10) == 110
        assert observer.execute(
            "SELECT balance FROM accounts WHERE id=1"
        ).fetchone() == (110,)

    def test_key_reuse_with_different_input_is_rejected(
        self, implementation: CreditOnce, database: Database
    ) -> None:
        _ = implementation(database, "key", 1, 10)

        with pytest.raises(ValueError):
            _ = implementation(database, "key", 1, 20)

    def test_failed_mutation_does_not_consume_idempotency_key(
        self, implementation: CreditOnce, database: Database, pg_connect: Connect
    ) -> None:
        with pytest.raises(LookupError):
            _ = implementation(database, "key", 99, 10)

        observer = pg_connect()
        assert observer.execute("SELECT count(*) FROM requests").fetchone() == (0,)
        assert implementation(observer, "key", 1, 10) == 110


@pytest.mark.contract("bound-transactions")
class TestTransactionBoundary:
    def test_failed_transfer_rolls_back_debit(
        self, implementation: Transfer, accounts: Database
    ) -> None:
        with pytest.raises(LookupError):
            implementation(accounts, 1, 99, 10)

        assert accounts.execute(
            "SELECT balance FROM accounts WHERE id=1"
        ).fetchone() == (100,)

    def test_transfer_commits_both_changes(
        self, implementation: Transfer, accounts: Database, pg_connect: Connect
    ) -> None:
        implementation(accounts, 1, 2, 10)

        assert pg_connect().execute(
            "SELECT balance FROM accounts ORDER BY id"
        ).fetchall() == [(90,), (60,)]


@pytest.mark.contract("parameterize-sql")
class TestSQLBinding:
    @pytest.fixture
    def users(self, pg: Database) -> Database:
        _ = pg.execute("CREATE TABLE users (id integer PRIMARY KEY, name text)")
        _ = pg.execute("INSERT INTO users VALUES (1, 'alice')")
        return pg

    def test_sql_metacharacters_are_data(
        self, implementation: FindUser, users: Database
    ) -> None:
        assert implementation(users, "' OR true --") == []

    def test_bound_value_matches(
        self, implementation: FindUser, users: Database
    ) -> None:
        assert implementation(users, "alice") == [(1,)]


@pytest.mark.contract("enforce-database-constraints")
class TestDatabaseConstraints:
    def test_duplicate_reference_is_rejected_by_database(
        self, implementation: CreateReservations, accounts: Database
    ) -> None:
        implementation(accounts)
        _ = accounts.execute("INSERT INTO reservations VALUES (1, 1, 'ref', 1)")

        with pytest.raises(psycopg.errors.UniqueViolation):
            _ = accounts.execute("INSERT INTO reservations VALUES (2, 1, 'ref', 1)")

    def test_invalid_quantity_and_owner_are_rejected(
        self, implementation: CreateReservations, accounts: Database
    ) -> None:
        implementation(accounts)

        with pytest.raises(psycopg.errors.CheckViolation):
            _ = accounts.execute("INSERT INTO reservations VALUES (1, 1, 'ref', 0)")
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            _ = accounts.execute("INSERT INTO reservations VALUES (1, 999, 'ref', 1)")


@pytest.mark.contract("prevent-lost-updates")
class TestLostUpdates:
    @pytest.fixture
    def documents(self, pg: Database) -> Database:
        _ = pg.execute(
            "CREATE TABLE documents (id bigint PRIMARY KEY, version integer, body text)"
        )
        _ = pg.execute("INSERT INTO documents VALUES (1, 1, 'initial')")
        return pg

    def test_stale_writer_cannot_overwrite_committed_edit(
        self, implementation: UpdateDocument, documents: Database, pg_connect: Connect
    ) -> None:
        second = pg_connect()
        assert implementation(documents, 1, 1, "first") == 2

        with pytest.raises(ValueError):
            _ = implementation(second, 1, 1, "stale")
        assert documents.execute("SELECT body FROM documents").fetchone() == ("first",)

    def test_current_version_update_is_accepted(
        self, implementation: UpdateDocument, documents: Database
    ) -> None:
        assert implementation(documents, 1, 1, "new") == 2


@pytest.mark.contract("retry-whole-transactions")
class TestTransactionRetry:
    def test_serialization_conflict_restarts_the_read(
        self, implementation: RunTransaction, accounts: Database, pg_connect: Connect
    ) -> None:
        second = pg_connect()
        reads: list[int] = []

        def edit(connection: Database) -> int:
            row = connection.execute(
                "SELECT balance FROM accounts WHERE id=1"
            ).fetchone()
            assert row is not None
            balance = row[0]
            assert isinstance(balance, int)
            reads.append(balance)
            if len(reads) == 1:
                _ = second.execute("UPDATE accounts SET balance=110 WHERE id=1")
            _ = connection.execute(
                "UPDATE accounts SET balance=%s WHERE id=1", (balance + 1,)
            )
            return balance + 1

        assert implementation(accounts, edit) == 111
        assert reads == [100, 110]

    def test_permanent_database_error_is_not_retried(
        self, implementation: RunTransaction, accounts: Database
    ) -> None:
        attempts = []

        def fail(connection: Database) -> None:
            attempts.append(1)
            _ = connection.execute("INSERT INTO accounts VALUES (1, 0)")

        with pytest.raises(psycopg.errors.UniqueViolation):
            implementation(accounts, fail)
        assert len(attempts) == 1


@pytest.mark.contract("batch-related-queries")
class TestBatchReads:
    def test_batch_avoids_one_query_per_parent(
        self, implementation: LoadItems, pg: Database
    ) -> None:
        _ = pg.execute("CREATE TABLE items (order_id bigint, sku text)")

        class CountedConnection:
            calls: int = 0

            def execute(
                self, query: LiteralString, params: tuple[list[int]], /
            ) -> Iterable[tuple[object, ...]]:
                self.calls += 1
                return pg.execute(query, params)

        counted = CountedConnection()

        assert implementation(counted, [1, 2, 3]) == {1: [], 2: [], 3: []}
        assert counted.calls <= 1

    def test_batch_includes_empty_parents(
        self, implementation: LoadItems, pg: Database
    ) -> None:
        _ = pg.execute("CREATE TABLE items (order_id bigint, sku text)")
        _ = pg.execute("INSERT INTO items VALUES (1, 'b'), (1, 'a'), (3, 'c')")

        assert implementation(pg, [1, 2]) == {1: ["a", "b"], 2: []}

    def test_batch_size_is_bounded(
        self, implementation: LoadItems, pg: Database
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation(pg, range(501))


@pytest.mark.contract("stable-cursor-pagination")
class TestPagination:
    def test_equal_timestamps_do_not_skip_rows(
        self, implementation: Page, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE events (created_at timestamptz, id bigint PRIMARY KEY)"
        )
        timestamp = datetime(2024, 1, 1, tzinfo=UTC)
        for identity in (1, 2, 3):
            _ = pg.execute("INSERT INTO events VALUES (%s, %s)", (timestamp, identity))

        first = implementation(pg, (timestamp, 0), size=2)
        second = implementation(pg, first[-1], size=2)
        assert [identity for _, identity in first + second] == [1, 2, 3]

    def test_invalid_page_size_is_rejected(
        self, implementation: Page, pg: Database
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation(pg, (datetime.now(UTC), 0), size=0)


@pytest.mark.contract("inspect-query-plans")
class TestQueryPlans:
    def test_plan_is_returned_without_query_execution(
        self, implementation: ExplainLookup, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE documents (tenant text, id bigint, body text, "
            "PRIMARY KEY (tenant, id))"
        )

        plan = implementation(pg, "a", 1)
        assert "Plan" in plan
        assert isinstance(plan["Plan"], dict)
        assert "Actual Rows" not in plan["Plan"]

    def test_explain_parameters_cannot_change_the_query(
        self, implementation: ExplainLookup, pg: Database
    ) -> None:
        _ = pg.execute("CREATE TABLE documents (tenant text, id bigint, body text)")

        assert "Plan" in implementation(pg, "'; DROP TABLE documents; --", 1)
        assert pg.execute("SELECT count(*) FROM documents").fetchone() == (0,)


@pytest.mark.contract("budget-connection-pools")
class TestPoolBudget:
    def test_pool_respects_per_process_budget(self, implementation: OpenPool) -> None:
        dsn = os.environ.get("PBG_POSTGRES_DSN")
        if dsn is None or dsn == "":
            pytest.skip("PBG_POSTGRES_DSN required")
        with implementation(dsn, database_limit=5, reserved=1, processes=2) as pool:
            with pool.connection(), pool.connection():
                from psycopg_pool import PoolTimeout

                with pytest.raises(PoolTimeout):
                    with pool.connection(timeout=0.05):
                        pytest.fail("exceeded per-process capacity")

    def test_exhausted_deployment_budget_is_rejected(
        self, implementation: OpenPool
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation("", database_limit=2, reserved=2, processes=1)


@pytest.mark.contract("expand-contract-migrations")
class TestExpansion:
    def test_expansion_keeps_old_writers_compatible(
        self,
        implementation: ExpandProfile,
        solution_module: ProfileModule,
        pg: Database,
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE profiles (id bigint PRIMARY KEY, name text NOT NULL)"
        )
        implementation(pg)
        _ = pg.execute("INSERT INTO profiles (id, name) VALUES (1, 'old')")

        assert solution_module.read_profile(pg, 1) == "old"

    def test_new_reader_prefers_backfilled_name(
        self,
        implementation: ExpandProfile,
        solution_module: ProfileModule,
        pg: Database,
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE profiles (id bigint PRIMARY KEY, name text NOT NULL)"
        )
        _ = pg.execute("INSERT INTO profiles VALUES (1, 'old')")
        implementation(pg)
        _ = pg.execute("UPDATE profiles SET display_name='new'")

        assert solution_module.read_profile(pg, 1) == "new"


@pytest.mark.contract("fence-stale-writers")
class TestFencing:
    def test_stale_token_cannot_overwrite_new_owner(
        self, implementation: FencedWrite, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE resources (id bigint PRIMARY KEY, token bigint, value text)"
        )
        _ = pg.execute("INSERT INTO resources VALUES (1, 0, 'initial')")
        implementation(pg, 1, 2, "new-owner")

        with pytest.raises(ValueError):
            implementation(pg, 1, 1, "stale-owner")
        assert pg.execute("SELECT value FROM resources").fetchone() == ("new-owner",)

    def test_fresh_token_is_persisted(
        self, implementation: FencedWrite, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE resources (id bigint PRIMARY KEY, token bigint, value text)"
        )
        _ = pg.execute("INSERT INTO resources VALUES (1, 0, 'initial')")

        implementation(pg, 1, 1, "new")
        assert pg.execute("SELECT token, value FROM resources").fetchone() == (1, "new")


@pytest.mark.contract("authorize-objects")
class TestObjectAuthorization:
    def test_other_owner_is_denied(
        self, implementation: OwnedDocument, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE private_documents (id bigint, owner text, body text)"
        )
        _ = pg.execute("INSERT INTO private_documents VALUES (1, 'alice', 'secret')")

        with pytest.raises(LookupError):
            _ = implementation(pg, "bob", 1)

    def test_owner_can_read(self, implementation: OwnedDocument, pg: Database) -> None:
        _ = pg.execute(
            "CREATE TABLE private_documents (id bigint, owner text, body text)"
        )
        _ = pg.execute("INSERT INTO private_documents VALUES (1, 'alice', 'secret')")

        assert implementation(pg, "alice", 1) == "secret"

    def test_missing_object_is_denied(
        self, implementation: OwnedDocument, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE private_documents (id bigint, owner text, body text)"
        )
        _ = pg.execute("INSERT INTO private_documents VALUES (1, 'alice', 'secret')")

        with pytest.raises(LookupError):
            _ = implementation(pg, "alice", 99)


@pytest.mark.contract("isolate-tenant-queries")
class TestTenantIsolation:
    def test_same_local_id_does_not_cross_tenants(
        self, implementation: TenantDocument, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE tenant_documents (tenant text, id bigint, body text, "
            "PRIMARY KEY (tenant, id))"
        )
        _ = pg.execute(
            "INSERT INTO tenant_documents VALUES ('a', 1, 'A'), ('b', 1, 'B')"
        )

        assert implementation(pg, "b", 1) == "B"

    def test_missing_tenant_is_denied(
        self, implementation: TenantDocument, pg: Database
    ) -> None:
        _ = pg.execute(
            "CREATE TABLE tenant_documents (tenant text, id bigint, body text)"
        )
        _ = pg.execute("INSERT INTO tenant_documents VALUES ('a', 1, 'A')")

        with pytest.raises(LookupError):
            _ = implementation(pg, "b", 1)


@pytest.mark.contract("serialize-migration-runners")
class TestMigrationLock:
    def test_second_migration_runner_is_rejected(
        self, implementation: RunMigration, pg: Database, pg_connect: Connect
    ) -> None:
        second = pg_connect()
        calls: list[str] = []

        def migration(connection: Database) -> None:
            with pytest.raises(RuntimeError):
                implementation(second, lambda other: calls.append("second"))
            calls.append("first")

        implementation(pg, migration)
        assert calls == ["first"]

    def test_failed_migration_rolls_back_and_releases_lock(
        self, implementation: RunMigration, pg: Database, pg_connect: Connect
    ) -> None:
        def fail(connection: Database) -> Never:
            _ = connection.execute("CREATE TABLE failed_migration (id integer)")
            raise ValueError

        with pytest.raises(ValueError):
            implementation(pg, fail)
        assert pg.execute("SELECT to_regclass('failed_migration')").fetchone() == (
            None,
        )
        calls: list[str] = []
        implementation(pg_connect(), lambda connection: calls.append("next"))
        assert calls == ["next"]
