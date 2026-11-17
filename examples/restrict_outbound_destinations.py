"""HTTP adapter: fetch only operator-configured destinations."""

from collections.abc import Callable, Mapping

import httpx


class ResponseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def __call__(self, url: str) -> bytes:
        response = self.client.get(url)
        _ = response.raise_for_status()
        return response.content


def fetch_configured(
    destination: str,
    destinations: Mapping[str, str],
    fetch: Callable[[str], bytes],
) -> bytes:
    """Application policy: callers choose IDs, not arbitrary URLs."""
    # Mapping is trusted startup configuration, not request data.
    return fetch(destinations[destination])


def fetch_destination(destination: str, destinations: Mapping[str, str]) -> bytes:
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        return fetch_configured(destination, destinations, ResponseFetcher(client))
