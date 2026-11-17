"""HTTP adapter: refuse redirects on a credentialed request."""

import httpx


def fetch_private(client: httpx.Client, url: str, token: str) -> bytes:
    response = client.get(
        url, headers={"Authorization": f"Bearer {token}"}, follow_redirects=False
    )
    if response.is_redirect:
        raise ValueError("redirect requires a new destination policy decision")
    _ = response.raise_for_status()
    return response.content
