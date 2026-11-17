import gzip
import os
import ssl
import threading
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override
from uuid import uuid4

import pika
import psycopg
import pytest
import trustme
from psycopg import sql

from tests.contracts import Broker, Connect, Database, HTTPRequest, HTTPServer


@pytest.fixture
def pg_connect() -> Generator[Connect, None, None]:
    dsn = os.environ.get("PBG_POSTGRES_DSN")
    if dsn is None or dsn == "":
        pytest.skip("set PBG_POSTGRES_DSN to a disposable PostgreSQL 16+ database")
    conninfo = dsn
    schema = "pbg_" + uuid4().hex
    connections: list[Database] = []
    with psycopg.Connection[tuple[object, ...]].connect(dsn, autocommit=True) as admin:
        _ = admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

        def connect() -> Database:
            connection = psycopg.Connection[tuple[object, ...]].connect(
                conninfo, autocommit=True
            )
            _ = connection.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )
            _ = connection.execute("SET statement_timeout = '5s'")
            connections.append(connection)
            return connection

        try:
            yield connect
        finally:
            for connection in connections:
                connection.close()
            _ = admin.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest.fixture
def pg(pg_connect: Connect) -> Database:
    return pg_connect()


@pytest.fixture
def accounts(pg: Database) -> Database:
    _ = pg.execute(
        "CREATE TABLE accounts (id bigint PRIMARY KEY, balance integer NOT NULL)"
    )
    _ = pg.execute("INSERT INTO accounts VALUES (1, 100), (2, 50)")
    return pg


@pytest.fixture
def broker() -> Generator[Broker, None, None]:
    url = os.environ.get("PBG_AMQP_URL")
    if url is None or url == "":
        pytest.skip("set PBG_AMQP_URL to a disposable RabbitMQ 4.1+ broker")
    connection = pika.BlockingConnection(pika.URLParameters(url))
    channel = connection.channel()
    channel.confirm_delivery()
    queue = channel.queue_declare(queue="", exclusive=True).method.queue
    try:
        yield connection, channel, queue
    finally:
        if connection.is_open:
            connection.close()


@pytest.fixture
def http_server(tmp_path: Path) -> Generator[HTTPServer, None, None]:
    servers: list[tuple[ThreadingHTTPServer, threading.Thread]] = []
    release = threading.Event()
    requests: list[HTTPRequest] = []
    ca = trustme.CA()
    ca.cert_pem.write_to_path(tmp_path / "ca.pem")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            requests.append((self.path, self.client_address, dict(self.headers)))
            body = gzip.compress(b"x" * 10000) if self.path == "/gzip" else b"ok"
            self.send_response(302 if self.path == "/redirect" else 200)
            self.send_header("Content-Length", str(len(body)))
            if self.path == "/redirect":
                self.send_header("Location", "/private")
            if self.path == "/gzip":
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            if self.path == "/slow":
                _ = release.wait(5)
            try:
                _ = self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def start(*, tls: bool = False) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        if tls:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ca.issue_cert("127.0.0.1").configure_cert(context)
            server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        return f"{'https' if tls else 'http'}://127.0.0.1:{server.server_port}"

    yield start, requests, tmp_path / "ca.pem"
    release.set()
    for server, thread in servers:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
