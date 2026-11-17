from pika import URLParameters
from pika.spec import BasicProperties

class _DeclareMethod:
    queue: str

class _DeclareResult:
    method: _DeclareMethod

class _GetResult:
    delivery_tag: int

class BlockingChannel:
    def confirm_delivery(self) -> None: ...
    def queue_declare(
        self,
        queue: str,
        passive: bool = False,
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: dict[str, str] | None = None,
    ) -> _DeclareResult: ...
    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: BasicProperties | None = None,
        mandatory: bool = False,
    ) -> None: ...
    def basic_get(
        self,
        queue: str,
        auto_ack: bool = False,
    ) -> tuple[_GetResult, BasicProperties, bytes] | tuple[None, None, None]: ...
    def basic_ack(self, delivery_tag: int = 0, multiple: bool = False) -> None: ...
    def basic_nack(
        self,
        delivery_tag: int = 0,
        multiple: bool = False,
        requeue: bool = True,
    ) -> None: ...
    def close(
        self, reply_code: int = 0, reply_text: str = "Normal shutdown"
    ) -> None: ...

class BlockingConnection:
    def __init__(self, parameters: URLParameters | None = None) -> None: ...
    @property
    def is_open(self) -> bool: ...
    def channel(self, channel_number: int | None = None) -> BlockingChannel: ...
    def close(
        self, reply_code: int = 200, reply_text: str = "Normal shutdown"
    ) -> None: ...
