# Integration tests

Install development dependencies with Python 3.12+:

```sh
uv sync --locked --group dev --python 3.12
```

The CLI has zero third-party runtime dependencies. HTTPX, Psycopg, Pika, PyJWT and
test TLS certificates are development/example dependencies only.

## Disposable services

Database and broker contracts use real PostgreSQL and RabbitMQ. Tests create
isolated schemas and exclusive queues; schema creation requires suitable database
privileges. Always point them at dedicated disposable test services.

For example, on a host with Docker and available ports:

```sh
docker run --detach --rm --name pbg-postgres \
  -e POSTGRES_PASSWORD=guidance -e POSTGRES_DB=guidance \
  -p 127.0.0.1:54329:5432 postgres:16-alpine
docker run --detach --rm --name pbg-rabbit \
  -p 127.0.0.1:56729:5672 rabbitmq:4.1-alpine
```

Wait for the services' startup health checks before running tests:

```sh
docker exec pbg-postgres pg_isready -U postgres -d guidance
docker exec pbg-rabbit rabbitmq-diagnostics -q ping
export PBG_POSTGRES_DSN='postgresql://postgres:guidance@127.0.0.1:54329/guidance'
export PBG_AMQP_URL='amqp://guest:guest@127.0.0.1:56729/%2F'
uv run --python 3.12 pytest
uv run --python 3.12 python -m evals.run calibrate
```

Stop only these example containers when finished:

```sh
docker stop pbg-postgres pbg-rabbit
```

The fixture closes database connections and drops its unique schema even after
failure. Broker queues are exclusive to the test connection and disappear when
it closes. The minimum service baseline exercised by CI is PostgreSQL 16 and
RabbitMQ 4.1; this is a compatibility test choice, not a production version policy.

## Missing services and CI

Without endpoint variables, service-dependent pytest cases are **skipped**.
This supports working on local examples, but does not verify the full catalog.
Calibration requires actual passed checks, so skipped service tests cannot
produce a passing calibration. A supplied but broken endpoint fails setup.

CI provisions both services for the Python 3.12/3.13/3.14 matrix and calibration.
HTTP/TLS checks run against local HTTP servers with temporary test CAs. No public
API or cloud credentials are needed. POSIX-specific file/process examples and
their tests currently run on Linux.

## Running one guide

The registry in `evals/tasks.toml` lists each guide's test file. Shared files use
task markers so the same contract can grade a candidate module:

```sh
uv run pytest tests/integration/test_database_contracts.py --task prevent-lost-updates
uv run python -m evals.run grade --task prevent-lost-updates \
  --solution examples/prevent_lost_updates.py --allow-code-execution
```

The grader forwards only the two explicit test endpoint variables in addition
to its existing reduced environment. Reports hash all applicable conftest files
and record declared example-library versions. Credentials themselves are not
added as report fields; candidate output may still contain sensitive information.

## What the checks establish

- Real database rollback, constraints, version predicates, serialization retry,
  idempotency records, inbox/outbox atomicity and advisory-lock coordination.
- Real RabbitMQ redelivery after commit failure and dead-letter routing.
- Real HTTP keep-alive, pool/read timeouts, TLS trust and redirect behavior.
- Real asyncio/thread/process cleanup and bounded data handling.

Small reference contracts do not establish production performance, power-loss
durability, lossless broker failover, a complete security audit, or agent uplift.
Each guide states what remains an application/deployment responsibility.
