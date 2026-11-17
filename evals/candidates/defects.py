"""One documented behavioral mutation per public guide contract.

Keep unrelated validation, results and cleanup intact. Calibration runs the full
contract and accepts only its declared failures. An unused public parameter is
intentional only when ignoring that policy is the mutation itself.
"""

import asyncio
import json
import logging
import math
import os
import random
import shutil
import signal
import ssl
import subprocess
import tempfile
import threading
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation, localcontext
from os import PathLike
from pathlib import Path
from typing import TypedDict, cast, override

import httpx
import jwt
from psycopg import Connection
from psycopg_pool import ConnectionPool

from examples.ack_after_commit import Acknowledgements
from examples.allowlist_log_fields import RequestEvent
from examples.batch_related_queries import ItemQuery
from examples.batch_related_queries import load_items as load_item_batch
from examples.bound_metric_labels import MetricLabels
from examples.coalesce_cache_misses import SingleFlight as CorrectSingleFlight
from examples.correlate_request_logs import correlation_id
from examples.distinguish_cache_misses import NotFound
from examples.expand_contract_migrations import read_profile
from examples.expire_cached_values import TTLCache as CorrectTTLCache
from examples.inspect_query_plans import JSONValue
from examples.isolate_request_context import request_id
from examples.own_resource_lifetimes import Closeable
from examples.preserve_error_causes import BackendUnavailable
from examples.quarantine_poison_messages import DeliveryChannel, Envelope
from examples.reject_overload import Admission as CorrectAdmission
from examples.stream_large_files import BinaryReader, BinaryWriter
from examples.validate_boundary_data import Order
from examples.validate_startup_configuration import Settings
from examples.version_message_payloads import UserEvent

type Database = Connection[tuple[object, ...]]


class LeakyRequestEvent(RequestEvent):
    headers: dict[str, str]


class CoupledHealth(TypedDict):
    live: bool
    ready: bool


__all__ = [
    "BackendUnavailable",
    "NotFound",
    "correlation_id",
    "read_profile",
    "request_id",
]


async def consume_bounded[T](
    source: AsyncIterable[T],
    handle: Callable[[T], Awaitable[None]],
    *,
    concurrency: int,
    buffer_size: int,
) -> None:
    """Mutation: omit queue capacity, retaining worker limits and ownership."""
    if concurrency < 1 or buffer_size < 1:
        raise ValueError("concurrency and buffer_size must be positive")
    queue: asyncio.Queue[tuple[T] | None] = asyncio.Queue()

    async def worker() -> None:
        while True:
            item = await queue.get()
            if item is None:
                return
            await handle(item[0])

    async with asyncio.TaskGroup() as group:
        for _ in range(concurrency):
            _ = group.create_task(worker())
        async for item in source:
            await queue.put((item,))
        for _ in range(concurrency):
            await queue.put(None)


async def fetch_and_store[T, R](
    fetch: Callable[[], Awaitable[T]],
    store: Callable[[T], Awaitable[R]],
    *,
    deadline: float,
) -> R:
    """Mutation: omit the preflight expiry check before starting callbacks."""
    if not math.isfinite(deadline):
        raise ValueError("deadline must be finite")
    async with asyncio.timeout_at(deadline):
        return await store(await fetch())


class TransientReadError(Exception):
    pass


async def retry_read[T](
    operation: Callable[[], Awaitable[T]],
    *,
    deadline: float,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> T:
    """Mutation: catch Exception instead of only TransientReadError."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if not math.isfinite(deadline):
        raise ValueError("deadline must be finite")
    if any(not math.isfinite(delay) or delay < 0 for delay in (base_delay, max_delay)):
        raise ValueError("backoff delays must be finite and nonnegative")
    loop = asyncio.get_running_loop()
    if deadline <= loop.time():
        raise TimeoutError("retry deadline already expired")
    attempt = 1
    ceiling = min(base_delay, max_delay)
    async with asyncio.timeout_at(deadline):
        while True:
            try:
                return await operation()
            except Exception:
                if attempt >= max_attempts:
                    raise
            delay = random.uniform(0, ceiling)
            if delay >= deadline - loop.time():
                raise TimeoutError("retry backoff cannot fit within the deadline")
            await asyncio.sleep(delay)
            ceiling = min(max_delay, ceiling * 2)
            attempt += 1


async def run_related[T](operations: Iterable[Callable[[], Awaitable[T]]]) -> list[T]:
    """Mutation: propagate a child failure without cancelling/joining siblings."""
    try:
        return await asyncio.gather(*(operation() for operation in operations))
    except Exception as error:
        raise ExceptionGroup("child failed", [error]) from None


async def call_blocking[R, *Args](operation: Callable[[*Args], R], *args: *Args) -> R:
    """Mutation: execute blocking work on the event-loop thread."""
    return operation(*args)


async def run_stoppable[T](worker: Callable[[threading.Event], T]) -> T:
    """Mutation: signal cooperative stop but propagate cancellation before joining."""
    stop = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(worker, stop))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        stop.set()
        raise


@contextmanager
def request_scope(value: str) -> Generator[None, None, None]:
    """Mutation: restore context only on normal exit, without a finally."""
    token = request_id.set(value)
    yield
    request_id.reset(token)


def credit_once(connection: Database, key: str, account: int, amount: int) -> int:
    """Mutation: fall through to the mutation instead of returning a saved result."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    with connection.transaction():
        row = connection.execute(
            "INSERT INTO requests (key, account, amount) VALUES (%s, %s, %s) "
            "ON CONFLICT (key) DO NOTHING RETURNING key",
            (key, account, amount),
        ).fetchone()
        if row is None:
            previous = connection.execute(
                "SELECT account, amount, result FROM requests WHERE key = %s",
                (key,),
            ).fetchone()
            assert previous is not None
            if previous[:2] != (account, amount):
                raise ValueError("idempotency key reused with different input")
        result = connection.execute(
            "UPDATE accounts SET balance = balance + %s "
            "WHERE id = %s RETURNING balance",
            (amount, account),
        ).fetchone()
        if result is None:
            raise LookupError(account)
        _ = connection.execute(
            "UPDATE requests SET result = %s WHERE key = %s", (result[0], key)
        )
        return cast(int, result[0])  # The SQL projection is an integer balance.


async def drain[T](
    tasks: Iterable[asyncio.Task[T]], *, grace: float
) -> list[T | BaseException]:
    """Mutation: cancel stragglers without joining them after the grace period."""
    if grace < 0:
        raise ValueError("grace must be nonnegative")
    owned = set(tasks)
    if len(owned) == 0:
        return []
    done, pending = await asyncio.wait(owned, timeout=grace)
    for task in pending:
        _ = task.cancel()
    results: list[T | BaseException] = []
    for task in done:
        if task.cancelled():
            results.append(asyncio.CancelledError())
        elif (error := task.exception()) is not None:
            results.append(error)
        else:
            results.append(task.result())
    return results


class Admission(CorrectAdmission):
    @override
    @asynccontextmanager
    async def enter(self) -> AsyncGenerator[None, None]:
        """Mutation: omit the admission-capacity check."""
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1


def fetch_batch(urls: Iterable[str]) -> list[str]:
    """Mutation: own a new client per URL instead of sharing it across the batch."""
    results: list[str] = []
    for url in urls:
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.get(url)
            _ = response.raise_for_status()
            results.append(response.text)
    return results


def make_http_client() -> httpx.Client:
    """Mutation: disable only the read timeout."""
    return httpx.Client(
        timeout=httpx.Timeout(connect=1, read=None, write=1, pool=0.1),
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        trust_env=False,
    )


def read_limited(client: httpx.Client, url: str, *, limit: int) -> bytes:
    """Mutation: trust Content-Length instead of counting decoded bytes."""
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    result = bytearray()
    with client.stream("GET", url) as response:
        _ = response.raise_for_status()
        if int(response.headers.get("content-length", 0)) > limit:
            raise ValueError("response too large")
        for chunk in response.iter_bytes(chunk_size=4096):
            result.extend(chunk)
    return bytes(result)


def fetch_verified(url: str, *, cafile: str | PathLike[str]) -> str:
    """Mutation: disable TLS peer verification on the configured trust context."""
    context = ssl.create_default_context(cafile=cafile)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with httpx.Client(verify=context, timeout=5, trust_env=False) as client:
        response = client.get(url)
        _ = response.raise_for_status()
        return response.text


def fetch_private(client: httpx.Client, url: str, token: str) -> bytes:
    """Mutation: follow redirects before the destination-policy check."""
    response = client.get(
        url, headers={"Authorization": f"Bearer {token}"}, follow_redirects=True
    )
    if response.is_redirect:
        raise ValueError("redirect requires a new destination policy decision")
    _ = response.raise_for_status()
    return response.content


def transfer(connection: Database, source: int, target: int, amount: int) -> None:
    """Mutation: omit the transaction enclosing both validated updates."""
    if amount <= 0 or source == target:
        raise ValueError("distinct accounts and a positive amount required")
    debit = connection.execute(
        "UPDATE accounts SET balance=balance-%s "
        "WHERE id=%s AND balance >= %s RETURNING id",
        (amount, source, amount),
    ).fetchone()
    if debit is None:
        raise ValueError("missing account or insufficient funds")
    if (
        connection.execute(
            "UPDATE accounts SET balance=balance+%s WHERE id=%s RETURNING id",
            (amount, target),
        ).fetchone()
        is None
    ):
        raise LookupError(target)


def find_user(connection: Database, name: str) -> list[tuple[int]]:
    """Mutation: interpolate the name into SQL instead of binding it."""
    # Deliberately interpolate before encoding: still vulnerable SQL, not binding.
    rows = connection.execute(
        f"SELECT id FROM users WHERE name = '{name}'".encode()
    ).fetchall()
    return cast(list[tuple[int]], rows)  # The SQL projection is a bigint id.


def create_reservations(connection: Database) -> None:
    """Mutation: omit only the reference's UNIQUE constraint."""
    _ = connection.execute(
        "CREATE TABLE reservations (id bigint PRIMARY KEY, "
        "account bigint NOT NULL REFERENCES accounts(id), reference text NOT NULL, "
        "quantity integer NOT NULL CHECK (quantity>0))"
    )


def update_document(
    connection: Database, identity: int, version: int, body: str
) -> int:
    """Mutation: omit the version predicate; version is intentionally unused."""
    row = connection.execute(
        "UPDATE documents SET body=%s, version=version+1 WHERE id=%s RETURNING version",
        (body, identity),
    ).fetchone()
    if row is None:
        raise ValueError("stale version or missing document")
    return cast(int, row[0])  # The SQL projection is an integer version.


def run_transaction[T](
    connection: Database, operation: Callable[[Database], T], *, attempts: int = 3
) -> T:
    """Mutation: omit retries after serialization/deadlock errors."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    with connection.transaction():
        _ = connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        return operation(connection)


def load_items(connection: ItemQuery, order_ids: Iterable[int]) -> dict[int, list[str]]:
    """Mutation: split a bounded batch into one correct query per distinct parent."""
    ids = list(dict.fromkeys(order_ids))
    if len(ids) > 500:
        raise ValueError("batch too large")
    return {
        identity: load_item_batch(connection, [identity])[identity] for identity in ids
    }


def page(
    connection: Database, after: tuple[datetime, int], *, size: int = 50
) -> list[tuple[datetime, int]]:
    """Mutation: omit the cursor's unique ID tie-breaker."""
    if not 1 <= size <= 100:
        raise ValueError("invalid page size")
    rows = connection.execute(
        "SELECT created_at, id FROM events WHERE created_at > %s "
        "ORDER BY created_at, id LIMIT %s",
        (after[0], size),
    ).fetchall()
    return cast(list[tuple[datetime, int]], rows)  # timestamptz, bigint projection.


def explain_lookup(
    connection: Database, tenant: str, identity: int
) -> dict[str, JSONValue]:
    """Mutation: add ANALYZE, executing the otherwise unchanged read."""
    row = connection.execute(
        "EXPLAIN (ANALYZE, FORMAT JSON) SELECT body FROM documents "
        "WHERE tenant=%s AND id=%s",
        (tenant, identity),
    ).fetchone()
    assert row is not None
    # PostgreSQL EXPLAIN FORMAT JSON produces a one-element array of plan objects.
    return cast(list[dict[str, JSONValue]], row[0])[0]


def open_pool(
    dsn: str, *, database_limit: int, reserved: int, processes: int
) -> ConnectionPool[Database]:
    """Mutation: give every process the entire unreserved deployment budget."""
    if processes < 1 or reserved < 0:
        raise ValueError("invalid process count or reserve")
    capacity = database_limit - reserved
    if capacity < 1:
        raise ValueError("no connection budget")
    return ConnectionPool(
        dsn,
        connection_class=Connection[tuple[object, ...]],
        min_size=0,
        max_size=capacity,
        max_waiting=capacity,
        timeout=1,
    )


def expand_profile(connection: Database) -> None:
    """Mutation: add NOT NULL too early, breaking old rows and old writers."""
    _ = connection.execute("ALTER TABLE profiles ADD COLUMN display_name text NOT NULL")


def process_delivery(
    channel: Acknowledgements, tag: int, connection: Database, message_id: str
) -> None:
    """Mutation: acknowledge after the INSERT but before the transaction commits."""
    with connection.transaction():
        _ = connection.execute("INSERT INTO effects VALUES (%s)", (message_id,))
        channel.basic_ack(delivery_tag=tag)


def apply_message(
    connection: Database, message_id: str, account: int, amount: int
) -> bool:
    """Mutation: ignore the inbox conflict and apply a redelivery's effect again."""
    with connection.transaction():
        _ = connection.execute(
            "INSERT INTO inbox (id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
            (message_id,),
        )
        row = connection.execute(
            "UPDATE accounts SET balance=balance+%s WHERE id=%s RETURNING id",
            (amount, account),
        ).fetchone()
        if row is None:
            raise LookupError(account)
        return True


def change_and_enqueue(
    connection: Database, account: int, amount: int, event_id: str
) -> None:
    """Mutation: omit the transaction joining the business update and outbox insert."""
    row = connection.execute(
        "UPDATE accounts SET balance=balance+%s WHERE id=%s RETURNING id",
        (amount, account),
    ).fetchone()
    if row is None:
        raise LookupError(account)
    _ = connection.execute(
        "INSERT INTO outbox (id, payload) VALUES (%s, %s)",
        (event_id, json.dumps({"account": account, "amount": amount})),
    )


def consume_json(
    channel: DeliveryChannel, tag: int, body: bytes, handle: Callable[[Envelope], None]
) -> bool:
    """Mutation: requeue malformed messages instead of dead-lettering them."""
    try:
        decoded: object = json.loads(body)
        if not isinstance(decoded, dict):
            raise ValueError("invalid envelope")
        message = cast(dict[str, object], decoded)  # JSON object keys are strings.
        if not isinstance(message.get("id"), str):
            raise ValueError("invalid envelope")
    except ValueError:
        channel.basic_nack(delivery_tag=tag, requeue=True)
        return False
    handle(cast(Envelope, message))  # The required id field was checked above.
    channel.basic_ack(delivery_tag=tag)
    return True


def decode_event(event: Mapping[str, object]) -> UserEvent:
    """Mutation: interpret unknown integer versions as v1."""
    version = event.get("version")
    if type(version) is not int:
        raise ValueError("integer version required")
    if version == 2:
        subject = event.get("subject")
        identity = (
            cast(dict[object, object], subject).get("id")
            if isinstance(subject, dict)
            else None
        )
    else:
        identity = event.get("user_id")
    if not isinstance(identity, str) or identity == "":
        raise ValueError("invalid identity")
    return {"user_id": identity}


def cache_key(tenant: str, subject: str, locale: str) -> str:
    """Mutation: use an unescaped delimiter between the key dimensions."""
    return f"{tenant}:{subject}:{locale}"


class TTLCache[K: Hashable, V](CorrectTTLCache[K, V]):
    @override
    def get(self, key: K) -> V:
        """Mutation: ignore expiry, keeping normal cache lookup/invalidation."""
        return self.entries[key][1]


class SingleFlight[K: Hashable, V]:
    """Mutation: give every waiter a unique key, retaining load ownership."""

    loads: CorrectSingleFlight[tuple[K, object], V]

    def __init__(self) -> None:
        self.loads = CorrectSingleFlight()

    async def get(self, key: K, load: Callable[[], Coroutine[object, object, V]]) -> V:
        return await self.loads.get((key, object()), load)

    async def close(self) -> None:
        await self.loads.close()


def lookup[K, V](
    cache: MutableMapping[K, V | None], key: K, load: Callable[[K], V]
) -> V | None:
    """Mutation: cache all loader errors as absence instead of only NotFound."""
    if key not in cache:
        try:
            cache[key] = load(key)
        except Exception:
            cache[key] = None
    return cache[key]


def fenced_write(connection: Database, identity: int, token: int, value: str) -> None:
    """Mutation: omit the token-order predicate."""
    row = connection.execute(
        "UPDATE resources SET token=%s, value=%s WHERE id=%s RETURNING id",
        (token, value, identity),
    ).fetchone()
    if row is None:
        raise ValueError("stale fencing token or missing resource")


def parse_order(value: object) -> Order:
    """Mutation: accept bool via isinstance(quantity, int)."""
    if not isinstance(value, dict):
        raise ValueError("expected sku and quantity only")
    fields = cast(dict[object, object], value)
    if set(fields) != {"sku", "quantity"}:
        raise ValueError("expected sku and quantity only")
    sku, quantity = fields["sku"], fields["quantity"]
    if not isinstance(sku, str) or not 1 <= len(sku) <= 64:
        raise ValueError("invalid sku")
    if not isinstance(quantity, int) or not 1 <= quantity <= 100:
        raise ValueError("invalid quantity")
    return {"sku": sku, "quantity": quantity}


async def collect_body(chunks: AsyncIterable[bytes], *, limit: int) -> bytes:
    """Mutation: enforce the limit per chunk rather than on the total body."""
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    result = bytearray()
    async for chunk in chunks:
        if len(chunk) > limit:
            raise ValueError("request body too large")
        result.extend(chunk)
    return bytes(result)


def patch_profile(
    current: Mapping[str, str | None], patch: object
) -> dict[str, str | None]:
    """Mutation: treat explicit null as if the nickname field were absent."""
    if not isinstance(patch, dict):
        raise ValueError("invalid patch")
    fields = cast(dict[object, object], patch)
    if len(set(fields) - {"nickname"}) != 0:
        raise ValueError("invalid patch")
    result = dict(current)
    if "nickname" in fields:
        value = fields["nickname"]
        if value is not None and not isinstance(value, str):
            raise ValueError("nickname must be a string or null")
        if value is not None:
            result["nickname"] = value
    return result


def parse_instant(value: str) -> datetime:
    """Mutation: assume UTC for a naive timestamp instead of rejecting it."""
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC)


def money(value: object) -> Decimal:
    """Mutation: round ties half-up instead of half-even."""
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("bounded decimal string required")
    try:
        with localcontext(Context(prec=28)):
            amount = Decimal(value)
            if not amount.is_finite() or amount.copy_abs() > Decimal("1000000000"):
                raise ValueError("invalid amount")
            return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValueError("invalid decimal amount") from error


def owned_document(connection: Database, principal: str, identity: int) -> str:
    """Mutation: omit authorization; principal is intentionally unused."""
    row = connection.execute(
        "SELECT body FROM private_documents WHERE id=%s", (identity,)
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The SQL projection is a text body.


def tenant_document(connection: Database, tenant: str, identity: int) -> str:
    """Mutation: omit tenant scoping; tenant is intentionally unused."""
    row = connection.execute(
        "SELECT body FROM tenant_documents WHERE id=%s ORDER BY tenant", (identity,)
    ).fetchone()
    if row is None:
        raise LookupError("document not found")
    return cast(str, row[0])  # The SQL projection is a text body.


def fetch_destination(destination: str, destinations: Mapping[str, str]) -> bytes:
    """Mutation: accept an unknown destination ID as a URL."""
    url = destinations.get(destination, destination)
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        response = client.get(url)
        _ = response.raise_for_status()
        return response.content


def read_owned_file(directory_fd: int, name: str) -> bytes:
    """Mutation: omit O_NOFOLLOW, retaining flat-filename validation."""
    if name == "" or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("a single filename is required")
    fd = os.open(name, os.O_RDONLY, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        return stream.read()


def verify_token(token: str | bytes, key: str | bytes) -> dict[str, object]:
    """Mutation: disable only audience verification."""
    return jwt.decode(
        token,
        key,
        algorithms=["HS256"],
        issuer="https://issuer.example",
        audience="backend",
        options={"require": ["exp", "iss", "aud", "sub"], "verify_aud": False},
    )


def request_event(
    method: str, route: str, status: int, headers: Mapping[str, str]
) -> LeakyRequestEvent:
    """Mutation: include request headers alongside the approved event fields."""
    return {
        "event": "request",
        "method": method,
        "route": route,
        "status": status,
        "headers": dict(headers),
    }


class CorrelationFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        """Mutation: use the background default instead of current correlation."""
        record.correlation_id = "-"
        return True


def metric_labels(route: str, status: int) -> MetricLabels:
    """Mutation: use the raw route instead of the finite route vocabulary."""
    return {
        "route": route,
        "status_class": f"{status // 100}xx" if 100 <= status <= 599 else "other",
    }


def read_backend[T](operation: Callable[[], T]) -> T:
    """Mutation: discard the OSError cause when translating the public error."""
    try:
        return operation()
    except OSError:
        raise BackendUnavailable("backend temporarily unavailable") from None


def health(*, started: bool, draining: bool, database_ready: bool) -> CoupledHealth:
    """Mutation: couple liveness to database readiness."""
    return {
        "live": database_ready,
        "ready": started and not draining and database_ready,
    }


def run_tool(executable: str, argument: str) -> str:
    """Mutation: interpolate argv into a shell command."""
    return subprocess.run(
        f"{executable} {argument}",
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


async def run_bounded(argv: Sequence[str], *, timeout: float, limit: int) -> bytes:
    """Mutation: omit output accounting, retaining timeout and process cleanup."""
    if timeout <= 0 or limit < 0:
        raise ValueError("invalid subprocess budget")
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    result = bytearray()
    assert process.stdout is not None
    try:
        async with asyncio.timeout(timeout):
            while (chunk := await process.stdout.read(4096)) != b"":
                result.extend(chunk)
            if await process.wait() != 0:
                raise RuntimeError("subprocess failed")
        return bytes(result)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        while await process.stdout.read(65536) != b"":
            pass
        _ = await process.wait()


def copy_stream(source: BinaryReader, destination: BinaryWriter, *, limit: int) -> int:
    """Mutation: check the total-byte budget after writing the current chunk."""
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    count = 0
    while (chunk := source.read(min(65536, limit - count + 1))) != b"":
        count += len(chunk)
        _ = destination.write(chunk)
        if count > limit:
            raise ValueError("file too large")
    return count


def replace_file(path: str | PathLike[str], content: bytes) -> None:
    """Mutation: publish the staged file before fsync succeeds."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            _ = stream.write(content)
            stream.flush()
            os.replace(temporary, path)
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def with_workspace[T](operation: Callable[[Path], T]) -> T:
    """Mutation: clean up only on successful completion, without a finally."""
    workspace = Path(tempfile.mkdtemp(prefix="pbg-defect-"))
    result = operation(workspace)
    shutil.rmtree(workspace)
    return result


def read_settings(environment: Mapping[str, str]) -> Settings:
    """Mutation: use truthiness to interpret a validated DEBUG string."""
    try:
        port = int(environment["PORT"])
    except (KeyError, ValueError) as error:
        raise ValueError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT out of range")
    mode = environment.get("DEBUG", "false").lower()
    if mode not in {"true", "false"}:
        raise ValueError("DEBUG must be true or false")
    return {"port": port, "debug": bool(mode)}


@contextmanager
def owned_resource[T: Closeable](
    open_resource: Callable[[], T],
) -> Generator[T, None, None]:
    """Mutation: close only on normal scope exit, without a finally."""
    resource = open_resource()
    yield resource
    resource.close()


@contextmanager
def open_resources[T: Closeable](
    factories: Iterable[Callable[[], T]],
) -> Generator[list[T], None, None]:
    """Mutation: begin unwinding protection only after every acquisition succeeds."""
    resources = [factory() for factory in factories]
    try:
        yield resources
    finally:
        for resource in reversed(resources):
            resource.close()


@asynccontextmanager
async def worker_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Mutation: omit closing the client at the end of its worker lifespan."""
    client = httpx.AsyncClient(timeout=5, trust_env=False)
    yield client
    # Lost ownership: a subsequent request remains possible.


def run_migration(connection: Database, migration: Callable[[Database], None]) -> None:
    """Mutation: omit the advisory lock, retaining the migration transaction."""
    with connection.transaction():
        migration(connection)
