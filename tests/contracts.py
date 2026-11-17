"""Static interfaces for independently loaded behavioral-contract candidates.

Pytest injects objects at runtime; annotations describe the required public
contract, never require a candidate to inherit a reference implementation.
"""

import asyncio
import logging
import threading
from collections.abc import (
    AsyncIterable,
    Awaitable,
    Callable,
    Coroutine,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal
from os import PathLike
from pathlib import Path
from typing import NotRequired, Protocol, TypedDict

import httpx
from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel
from psycopg import Connection
from psycopg_pool import ConnectionPool

from examples.ack_after_commit import Acknowledgements
from examples.allowlist_log_fields import RequestEvent
from examples.batch_related_queries import ItemQuery
from examples.bound_metric_labels import MetricLabels
from examples.inspect_query_plans import JSONValue
from examples.own_resource_lifetimes import Closeable
from examples.quarantine_poison_messages import DeliveryChannel, Envelope
from examples.separate_health_probes import Health
from examples.stream_large_files import BinaryReader, BinaryWriter
from examples.validate_boundary_data import Order
from examples.validate_startup_configuration import Settings
from examples.version_message_payloads import UserEvent

type Database = Connection[tuple[object, ...]]
type Connect = Callable[[], Database]
type Broker = tuple[BlockingConnection, BlockingChannel, str]
type HTTPRequest = tuple[str, tuple[str, int], dict[str, str]]


class StartHTTP(Protocol):
    def __call__(self, *, tls: bool = False) -> str: ...


type HTTPServer = tuple[StartHTTP, list[HTTPRequest], Path]


class ConsumeBounded(Protocol):
    async def __call__[T](
        self,
        source: AsyncIterable[T],
        handle: Callable[[T], Awaitable[None]],
        *,
        concurrency: int,
        buffer_size: int,
    ) -> None: ...


class FetchAndStore(Protocol):
    async def __call__[T, R](
        self,
        fetch: Callable[[], Awaitable[T]],
        store: Callable[[T], Awaitable[R]],
        *,
        deadline: float,
    ) -> R: ...


class RetryRead(Protocol):
    async def __call__[T](
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        deadline: float,
        max_attempts: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 2.0,
    ) -> T: ...


class RetrySettings(TypedDict):
    max_attempts: NotRequired[int]
    base_delay: NotRequired[float]
    max_delay: NotRequired[float]


class RetryModule(Protocol):
    TransientReadError: type[Exception]


class RunRelated(Protocol):
    async def __call__[T](
        self, operations: Iterable[Callable[[], Coroutine[object, object, T]]]
    ) -> list[T]: ...


class CallBlocking(Protocol):
    async def __call__[R, *Args](
        self, operation: Callable[[*Args], R], *args: *Args
    ) -> R: ...


class RunStoppable(Protocol):
    async def __call__[T](self, worker: Callable[[threading.Event], T]) -> T: ...


type RequestScope = Callable[[str], AbstractContextManager[None]]


class ContextModule(Protocol):
    request_id: ContextVar[str | None]


class Drain(Protocol):
    async def __call__[T](
        self, tasks: Iterable[asyncio.Task[T]], *, grace: float
    ) -> list[T | BaseException]: ...


class Gate(Protocol):
    def enter(self) -> AbstractAsyncContextManager[None]: ...


type Admission = Callable[[int], Gate]
type FetchBatch = Callable[[Iterable[str]], list[str]]
type MakeHTTPClient = Callable[[], httpx.Client]


class ReadLimited(Protocol):
    def __call__(self, client: httpx.Client, url: str, *, limit: int) -> bytes: ...


class FetchVerified(Protocol):
    def __call__(self, url: str, *, cafile: str | PathLike[str]) -> str: ...


type FetchPrivate = Callable[[httpx.Client, str, str], bytes]
type FetchDestination = Callable[[str, Mapping[str, str]], bytes]
type WorkerClient = Callable[[], AbstractAsyncContextManager[httpx.AsyncClient]]
type CreditOnce = Callable[[Database, str, int, int], int]
type Transfer = Callable[[Database, int, int, int], None]
type FindUser = Callable[[Database, str], list[tuple[int]]]
type CreateReservations = Callable[[Database], None]
type UpdateDocument = Callable[[Database, int, int, str], int]


class RunTransaction(Protocol):
    def __call__[T](
        self,
        connection: Database,
        operation: Callable[[Database], T],
        *,
        attempts: int = 3,
    ) -> T: ...


type LoadItems = Callable[[ItemQuery, Iterable[int]], dict[int, list[str]]]


class Page(Protocol):
    def __call__(
        self, connection: Database, after: tuple[datetime, int], *, size: int = 50
    ) -> list[tuple[datetime, int]]: ...


type ExplainLookup = Callable[[Database, str, int], dict[str, JSONValue]]


class OpenPool(Protocol):
    def __call__(
        self,
        dsn: str,
        *,
        database_limit: int,
        reserved: int,
        processes: int,
    ) -> ConnectionPool[Database]: ...


type ExpandProfile = Callable[[Database], None]


class ProfileModule(Protocol):
    def read_profile(self, connection: Database, identity: int) -> str: ...


type FencedWrite = Callable[[Database, int, int, str], None]
type OwnedDocument = Callable[[Database, str, int], str]
type TenantDocument = Callable[[Database, str, int], str]
type RunMigration = Callable[[Database, Callable[[Database], None]], None]
type ProcessDelivery = Callable[[Acknowledgements, int, Database, str], None]
type ApplyMessage = Callable[[Database, str, int, int], bool]
type ChangeAndEnqueue = Callable[[Database, int, int, str], None]
type ConsumeJSON = Callable[
    [DeliveryChannel, int, bytes, Callable[[Envelope], None]], bool
]
type DecodeEvent = Callable[[Mapping[str, object]], UserEvent]
type CacheKey = Callable[[str, str, str], str]


class Cache(Protocol):
    def put(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> str: ...
    def invalidate(self, key: str) -> None: ...


class TTLCache(Protocol):
    def __call__(self, *, ttl: float, clock: Callable[[], float]) -> Cache: ...


class Flight(Protocol):
    async def get(
        self, key: str, load: Callable[[], Coroutine[object, object, int]]
    ) -> int: ...
    async def close(self) -> None: ...


type SingleFlight = Callable[[], Flight]


class Lookup(Protocol):
    def __call__[K, V](
        self, cache: MutableMapping[K, V | None], key: K, load: Callable[[K], V]
    ) -> V | None: ...


class NotFoundModule(Protocol):
    NotFound: type[Exception]


type ParseOrder = Callable[[object], Order]


class CollectBody(Protocol):
    async def __call__(self, chunks: AsyncIterable[bytes], *, limit: int) -> bytes: ...


type PatchProfile = Callable[[Mapping[str, str | None], object], dict[str, str | None]]
type ParseInstant = Callable[[str], datetime]
type Money = Callable[[object], Decimal]
type ReadOwnedFile = Callable[[int, str], bytes]
type VerifyToken = Callable[[str | bytes, str | bytes], dict[str, object]]
type MakeRequestEvent = Callable[[str, str, int, Mapping[str, str]], RequestEvent]


class Filter(Protocol):
    def filter(self, record: logging.LogRecord) -> bool: ...


type CorrelationFilter = Callable[[], Filter]


class CorrelationModule(Protocol):
    correlation_id: ContextVar[str]


type MakeMetricLabels = Callable[[str, int], MetricLabels]


class ReadBackend(Protocol):
    def __call__[T](self, operation: Callable[[], T]) -> T: ...


class ErrorModule(Protocol):
    BackendUnavailable: type[Exception]


class ProbeHealth(Protocol):
    def __call__(
        self, *, started: bool, draining: bool, database_ready: bool
    ) -> Health: ...


type RunTool = Callable[[str, str], str]


class RunBounded(Protocol):
    async def __call__(
        self, argv: Sequence[str], *, timeout: float, limit: int
    ) -> bytes: ...


class CopyStream(Protocol):
    def __call__(
        self, source: BinaryReader, destination: BinaryWriter, *, limit: int
    ) -> int: ...


type ReplaceFile = Callable[[str | PathLike[str], bytes], None]


class WithWorkspace(Protocol):
    def __call__[T](self, operation: Callable[[Path], T]) -> T: ...


type ReadSettings = Callable[[Mapping[str, str]], Settings]


class OwnedResource(Protocol):
    def __call__[T: Closeable](
        self, open_resource: Callable[[], T]
    ) -> AbstractContextManager[T]: ...


class OpenResources(Protocol):
    def __call__[T: Closeable](
        self, factories: Iterable[Callable[[], T]]
    ) -> AbstractContextManager[list[T]]: ...
