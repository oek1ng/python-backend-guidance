"""HTTP adapter: trust an explicit CA without disabling verification."""

import ssl
from os import PathLike

import httpx


def fetch_verified(url: str, *, cafile: str | PathLike[str]) -> str:
    context = ssl.create_default_context(cafile=cafile)
    with httpx.Client(verify=context, timeout=5, trust_env=False) as client:
        response = client.get(url)
        _ = response.raise_for_status()
        return response.text
