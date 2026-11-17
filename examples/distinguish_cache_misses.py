"""Application workflow: only a definitive absence is eligible for caching."""

from collections.abc import Callable, Hashable, MutableMapping


class NotFound(Exception):
    pass


def lookup[K: Hashable, V](
    cache: MutableMapping[K, V | None], key: K, load: Callable[[K], V]
) -> V | None:
    if key in cache:
        return cache[key]
    value: V | None
    try:
        value = load(key)
    except NotFound:
        value = None
    cache[key] = value
    return value
