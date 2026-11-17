"""Composition root: own one HTTP client for a batch of requests."""

from collections.abc import Callable, Iterable

import httpx


class TextFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def __call__(self, url: str) -> str:
        response = self.client.get(url)
        _ = response.raise_for_status()
        return response.text


def fetch_with_reader(
    fetch_text: Callable[[str], str], urls: Iterable[str]
) -> list[str]:
    """Application workflow: read borrowed URLs through an injected port."""
    return [fetch_text(url) for url in urls]


def fetch_batch(urls: Iterable[str]) -> list[str]:
    with httpx.Client(timeout=5, trust_env=False) as client:
        return fetch_with_reader(TextFetcher(client), urls)
