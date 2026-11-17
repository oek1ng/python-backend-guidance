"""Composition root: configure explicit HTTP client phase budgets."""

import httpx


def make_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(connect=1, read=0.1, write=1, pool=0.1),
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        trust_env=False,
    )
