# Public contracts for all 60 guides

Implement only the selected task's interface in a Python 3.12+ module. The
registry maps each task to its entrypoint and reusable tests. Implementations may
use a different algorithm when they satisfy the same observable behavior.
These are public solution contracts, not a coding-agent runner or hidden exam.
Keep the selected prompt, interface, and task budget identical in guided and
unguided runs; do not prescribe an algorithm in the prompt.

Database examples use PostgreSQL 16+ and Psycopg 3 on idle, autocommit connections.
The tests create isolated schemas and supply tables. Each transaction helper owns
the entire transaction. Network examples use HTTPX 0.28; message adapters use
RabbitMQ 4.1+ with Pika. The CLI itself needs none of these dependencies.

| Task | Interface and observable contract |
| --- | --- |
| bound-concurrent-work | `await consume_bounded(source, handle, *, concurrency, buffer_size)`: process a large async input stream without unbounded pending work. Both limits must be positive; input may include `None`. Permit concurrent handlers when work is available; no more than `concurrency` active handlers and `concurrency + buffer_size + 1` produced-but-unfinished items when handlers are blocked, including a producer-held item. Return after completion or failure and cooperative cleanup; source/handler errors propagate directly or in an exception group, and cancellation leaves no active handlers. Ordering is not required. Python 3.12+ stdlib only, no framework dependency; source and shared clients remain caller-owned, with no durable-delivery guarantee. |
| apply-operation-deadline | `await fetch_and_store(fetch, store, *, deadline)`: fetch a payload and pass it to the async store callback, returning the store result within one total waiting budget. `deadline` is a finite absolute timestamp from the current event loop's monotonic clock; neither stage may start after expiry. Both stages share the budget; expiry raises `TimeoutError`, ordinary errors and external cancellation propagate, and cooperative cleanup is awaited. Python 3.12+ stdlib only; shared clients remain caller-owned, with no rollback or hard real-time guarantee. |
| retry-transient-reads | Export `TransientReadError(Exception)` and `await retry_read(operation, *, deadline, max_attempts=3, base_delay=0.1, max_delay=2.0)`: recover a known repeatable, read-only async callback from only that transient marker, returning its first successful value. Count the initial call toward positive integer `max_attempts`; exhaustion preserves the last transient error, while other errors and cancellation never cause another attempt. Use capped exponential full jitter: the first ceiling is `min(base_delay, max_delay)`, doubling up to `max_delay`; draw with `random.uniform(0, ceiling)` and wait with `asyncio.sleep()` as controllable grading boundaries. Delays must be finite and nonnegative. A finite absolute event-loop-monotonic `deadline` covers attempts and waits; an expired budget or backoff that cannot fit raises `TimeoutError` before another attempt. Python 3.12+ stdlib only; no HTTP-error/mutation classification, exactly-once, rollback, deployment-wide retry quota, or noncooperative cancellation guarantee. |
| own-child-tasks | `await run_related(operations)`: call zero-argument coroutine factories; return results in input order, join cancelled siblings before propagating an exception group. |
| offload-blocking-io | `await call_blocking(operation, *args)`: preserve result/error while permitting the event loop to progress during a blocking call. |
| stop-thread-work | `await run_stoppable(worker)`: worker accepts a threading stop event; cancellation signals it and joins before propagating cancellation. Worker must cooperate. |
| isolate-request-context | `with request_scope(value)`: set exported `request_id` ContextVar temporarily, restore its previous value on every exit; default is None. |
| deduplicate-mutations | `credit_once(connection, key, account, amount)`: positive credit and durable result recorded atomically in accounts/requests; duplicate input returns original result, conflicting reuse raises ValueError. |
| drain-on-shutdown | `await drain(tasks, grace=seconds)`: await completion up to grace, cancel and join remaining tasks, return results/exceptions. |
| reject-overload | `Admission(capacity).enter()`: async scope with immediate RuntimeError when full; release capacity after all exits. |
| reuse-http-clients | `fetch_batch(urls)`: return response text in order; reuse a keep-alive connection within a batch and close owned client. |
| set-http-timeouts | `make_http_client()`: caller-owned HTTPX client, one connection, bounded pool wait and stalled-body read (0.1s in this example). |
| bound-response-bytes | `read_limited(client, url, limit=n)`: bytes, at most n decoded bytes, reject larger responses with ValueError; close the response on failure. |
| verify-tls | `fetch_verified(url, cafile=path)`: accept the explicitly trusted CA, reject untrusted TLS, return response text. |
| control-redirects | `fetch_private(client, url, token)`: bearer request, return bytes, refuse redirects with ValueError before issuing another request. |
| bound-transactions | `transfer(connection, source, target, amount)`: positive transfer between distinct accounts, commit both updates or neither; missing target raises LookupError. |
| parameterize-sql | `find_user(connection, name)`: list of matching `(id,)` rows; SQL metacharacters in name remain data. |
| enforce-database-constraints | `create_reservations(connection)`: create id PK, account FK, unique required reference, required positive quantity constraints. |
| prevent-lost-updates | `update_document(connection, id, version, body)`: atomically replace only matching version, return next version, otherwise ValueError. |
| retry-whole-transactions | `run_transaction(connection, operation, attempts=3)`: SERIALIZABLE transaction; retry whole operation for serialization/deadlock errors, propagate permanent errors. |
| batch-related-queries | `load_items(connection, ids)`: at most 500 distinct IDs; one query maximum; mapping includes empty parents and sorted SKUs. |
| stable-cursor-pagination | `page(connection, after, size=50)`: ascending `(created_at,id)` keyset, exclusive cursor, size 1..100. |
| inspect-query-plans | `explain_lookup(connection, tenant, id)`: JSON plan mapping for a parameterized read; do not execute the read through ANALYZE. |
| budget-connection-pools | `open_pool(dsn, database_limit=n, reserved=r, processes=p)`: caller-owned pool with floor((n-r)/p) maximum connections; reject no-capacity configurations. |
| expand-contract-migrations | `expand_profile(connection)` and `read_profile(connection,id)`: nullable display_name addition; old inserts still work; read new name with fallback to name. |
| ack-after-commit | `process_delivery(channel,tag,connection,message_id)`: insert effects id atomically, then manual ack; commit failure must leave delivery unacknowledged. |
| deduplicate-deliveries | `apply_message(connection,id,account,amount)`: inbox and account update atomic; True for first application, False for duplicate; missing account rolls back inbox. |
| transactional-outbox | `change_and_enqueue(connection,account,amount,event_id)`: account change and JSON event in outbox commit together or neither. |
| quarantine-poison-messages | `consume_json(channel,tag,body,handle)`: malformed object/id => nack without requeue and False; successful handle => ack and True; handler error leaves message unacked. |
| version-message-payloads | `decode_event(mapping)`: normalize v1 user_id and v2 subject.id to user_id; reject unknown/noninteger version or invalid identity. |
| scope-cache-keys | `cache_key(tenant,subject,locale)`: stable text identity with unambiguous boundaries and all three dimensions. |
| expire-cached-values | `TTLCache(ttl=n,clock=callable)` with put/get/invalidate: expire at the exact TTL boundary, KeyError on miss, invalidation immediate. |
| coalesce-cache-misses | `SingleFlight` with async get(key,load)/close(): one in-flight loader per key, waiter cancellation does not cancel another waiter's work, failed loads can be retried, close joins owned tasks and their cooperative cleanup. |
| distinguish-cache-misses | `lookup(cache,key,load)` and exported NotFound: cache success/definitive absence (None), propagate other errors without inserting a cache entry. |
| fence-stale-writers | `fenced_write(connection,id,token,value)`: storage atomically accepts only token strictly greater than stored token; otherwise ValueError. |
| validate-boundary-data | `parse_order(mapping)`: exactly sku and quantity; sku string length 1..64, quantity integer excluding bool in 1..100, otherwise ValueError. |
| bound-incoming-bodies | `await collect_body(chunks,limit=n)`: async byte chunks, return at most n bytes, otherwise ValueError. |
| distinguish-patch-null | `patch_profile(current,patch)`: absent nickname preserves, None clears, string replaces; do not mutate current; reject unknown fields. |
| use-aware-timestamps | `parse_instant(text)`: require ISO offset, normalize to aware UTC, reject naive timestamp. |
| quantize-money | `money(text)`: finite decimal string, absolute value <=1e9, two digits with HALF_EVEN; reject floats, nonfinite and oversized inputs. |
| authorize-objects | `owned_document(connection,principal,id)`: return body only for owner; missing or unauthorized => LookupError. |
| isolate-tenant-queries | `tenant_document(connection,tenant,id)`: scope by tenant and local ID; missing => LookupError. |
| restrict-outbound-destinations | `fetch_destination(id, trusted_mapping)`: configured URL only, unknown id => KeyError; refuse redirects; return bytes. |
| confine-file-access | `read_owned_file(directory_fd,name)`: POSIX flat name only, reject traversal and symlinks, return bytes. |
| verify-token-claims | `verify_token(token,key)`: HS256 only, issuer https://issuer.example, audience backend; require exp/iss/aud/sub and validate expiration. |
| allowlist-log-fields | `request_event(method,route,status,headers)`: only event=request, method, route, status; exclude all header values. |
| correlate-request-logs | `CorrelationFilter.filter(record)` and exported correlation_id ContextVar: snapshot current correlation ID on record; default "-"; return True. |
| bound-metric-labels | `metric_labels(route,status)`: finite /orders, /orders/{id}, /health vocabulary, else unmatched; status classes 1xx..5xx or other. |
| preserve-error-causes | `read_backend(operation)` and BackendUnavailable: OSError becomes fixed public error with original __cause__; unrelated errors propagate. |
| separate-health-probes | `health(started=bool,draining=bool,database_ready=bool)`: live stays true; ready requires started, not draining and dependency ready. |
| avoid-shell-interpolation | `run_tool(executable,argument)`: literal single argument, stdout text, nonzero status raises CalledProcessError. |
| bound-subprocess-resources | `await run_bounded(argv,timeout=seconds,limit=n)`: POSIX bytes output, bound time/output, nonzero failure; on timeout, failure or external cancellation kill the owned process group and reap the direct child, including when descendants hold pipes after the leader exits. |
| stream-large-files | `copy_stream(source,destination,limit=n)`: bounded reads, return bytes copied, reject exceeding limit without writing excess; caller owns streams. |
| replace-files-atomically | `replace_file(path,bytes)`: POSIX same-directory staging, sync before replace, old file survives pre-replace failure, remove staging file. |
| own-temporary-files | `with_workspace(operation)`: pass private Path directory, return operation result, clean up on success/error. |
| validate-startup-configuration | `read_settings(environment)`: PORT integer 1..65535, DEBUG true/false text (default false); invalid => ValueError. |
| own-resource-lifetimes | `with owned_resource(factory)`: yield resource and close on every exit, exactly once. |
| unwind-partial-startup | `with open_resources(factories)`: yield acquired resources; unwind in reverse order after later acquisition failure or body exit. |
| scope-process-resources | `async with worker_client()`: fresh HTTPX AsyncClient per worker lifespan, closed on exit. |
| serialize-migration-runners | `run_migration(connection,callback)`: mutually exclusive transaction-scoped PostgreSQL advisory lock, busy => RuntimeError; rollback and release on failure. |

## Running one contract

```sh
uv run pytest tests/test_backend_data.py --task quantize-money
uv run python -m evals.run grade --task quantize-money \
  --solution examples/quantize_money.py --allow-code-execution
```

The test path is shared by related contracts; `--task` selects only matching
markers. Service-dependent contracts require the disposable endpoints documented
in [integration testing](../docs/integration-testing.md). Missing endpoints cause
skips in pytest, and cannot count as a passed calibration.
