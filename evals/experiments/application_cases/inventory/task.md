# Inventory import

Fix `solution.py` in this small application. Keep its public `sync_inventory`
interface and Python 3.12+ annotations:

```python
async def sync_inventory[T](
    records: AsyncIterable[T],
    persist: Callable[[T], Awaitable[None]],
    *,
    workers: int,
    pending: int,
) -> int: ...
```

Each item must be persisted exactly once on success; return the number of
successfully persisted items. `records` may yield `None`. Work may complete in
any order. `workers` and `pending` must be positive integers; reject invalid
configuration before reading the source.

The source can be arbitrarily large. At most `workers` calls to `persist` may be
active, and at most `workers + pending + 1` records may have been produced but
not finished while handlers are blocked. Do not consume the complete input
before processing. If the source or a handler fails, propagate the error and
wait for started handlers to clean up. Parent cancellation must do the same.
The caller owns the source and the persistence client. No durability or
retry-on-failure guarantee is requested. Python 3.12+ stdlib only.
