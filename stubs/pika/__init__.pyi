"""The Pika surface exercised by the real RabbitMQ contract tests (Pika 1.3–1.x).

Pika ships no py.typed marker. Keep these narrow stubs in sync with its public
blocking-adapter API; they do not replace the installed runtime package.
"""

from pika.adapters.blocking_connection import BlockingConnection as BlockingConnection

class URLParameters:
    def __init__(self, url: str) -> None: ...
