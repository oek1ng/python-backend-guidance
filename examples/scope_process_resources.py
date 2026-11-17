"""Composition root: initialize clients inside the worker's lifespan."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx


@asynccontextmanager
async def worker_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
        yield client
