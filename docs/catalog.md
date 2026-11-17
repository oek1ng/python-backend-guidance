# Guide catalog

60 focused draft guides for Python 3.12+, grouped into 12 backend areas.
Each guide contains applicability, actionable rules, an executable example,
limitations, verification instructions and checked sources. Examples are teaching
units, not complete production services. Independent review is still required.

Use `python-backend-guidance search "<capability>"` and retrieve only the relevant
guides. `runtime = "sync"` identifies a synchronous recipe; `any` is independent
of concurrency runtime. Library, service and POSIX requirements are explicit.

## Concurrency

- [Bound concurrent work](../src/python_backend_guidance/guides/bound-concurrent-work.md)
- [Own child tasks](../src/python_backend_guidance/guides/own-child-tasks.md)
- [Offload blocking I/O](../src/python_backend_guidance/guides/offload-blocking-io.md)
- [Stop thread work](../src/python_backend_guidance/guides/stop-thread-work.md)
- [Isolate request context](../src/python_backend_guidance/guides/isolate-request-context.md)

## Reliability

- [Apply an operation deadline](../src/python_backend_guidance/guides/apply-operation-deadline.md)
- [Retry transient reads](../src/python_backend_guidance/guides/retry-transient-reads.md)
- [Deduplicate mutations](../src/python_backend_guidance/guides/deduplicate-mutations.md)
- [Drain on shutdown](../src/python_backend_guidance/guides/drain-on-shutdown.md)
- [Reject overload](../src/python_backend_guidance/guides/reject-overload.md)

## HTTP clients

- [Reuse HTTP clients](../src/python_backend_guidance/guides/reuse-http-clients.md)
- [Set HTTP timeouts](../src/python_backend_guidance/guides/set-http-timeouts.md)
- [Bound response bytes](../src/python_backend_guidance/guides/bound-response-bytes.md)
- [Verify TLS](../src/python_backend_guidance/guides/verify-tls.md)
- [Control redirects](../src/python_backend_guidance/guides/control-redirects.md)

## Database correctness

- [Bound transactions](../src/python_backend_guidance/guides/bound-transactions.md)
- [Parameterize SQL](../src/python_backend_guidance/guides/parameterize-sql.md)
- [Enforce database constraints](../src/python_backend_guidance/guides/enforce-database-constraints.md)
- [Prevent lost updates](../src/python_backend_guidance/guides/prevent-lost-updates.md)
- [Retry whole transactions](../src/python_backend_guidance/guides/retry-whole-transactions.md)

## Database performance and evolution

- [Batch related queries](../src/python_backend_guidance/guides/batch-related-queries.md)
- [Stable cursor pagination](../src/python_backend_guidance/guides/stable-cursor-pagination.md)
- [Inspect query plans](../src/python_backend_guidance/guides/inspect-query-plans.md)
- [Budget connection pools](../src/python_backend_guidance/guides/budget-connection-pools.md)
- [Expand–contract migrations](../src/python_backend_guidance/guides/expand-contract-migrations.md)

## Messages

- [Acknowledge after commit](../src/python_backend_guidance/guides/ack-after-commit.md)
- [Deduplicate deliveries](../src/python_backend_guidance/guides/deduplicate-deliveries.md)
- [Transactional outbox](../src/python_backend_guidance/guides/transactional-outbox.md)
- [Quarantine poison messages](../src/python_backend_guidance/guides/quarantine-poison-messages.md)
- [Version message payloads](../src/python_backend_guidance/guides/version-message-payloads.md)

## Caches and shared state

- [Scope cache keys](../src/python_backend_guidance/guides/scope-cache-keys.md)
- [Expire cached values](../src/python_backend_guidance/guides/expire-cached-values.md)
- [Coalesce cache misses](../src/python_backend_guidance/guides/coalesce-cache-misses.md)
- [Distinguish cache misses](../src/python_backend_guidance/guides/distinguish-cache-misses.md)
- [Fence stale writers](../src/python_backend_guidance/guides/fence-stale-writers.md)

## Input and data contracts

- [Validate boundary data](../src/python_backend_guidance/guides/validate-boundary-data.md)
- [Bound incoming bodies](../src/python_backend_guidance/guides/bound-incoming-bodies.md)
- [Distinguish PATCH null](../src/python_backend_guidance/guides/distinguish-patch-null.md)
- [Use aware timestamps](../src/python_backend_guidance/guides/use-aware-timestamps.md)
- [Quantize money](../src/python_backend_guidance/guides/quantize-money.md)

## Security

- [Authorize objects](../src/python_backend_guidance/guides/authorize-objects.md)
- [Isolate tenant queries](../src/python_backend_guidance/guides/isolate-tenant-queries.md)
- [Restrict outbound destinations](../src/python_backend_guidance/guides/restrict-outbound-destinations.md)
- [Confine file access](../src/python_backend_guidance/guides/confine-file-access.md)
- [Verify token claims](../src/python_backend_guidance/guides/verify-token-claims.md)

## Observability

- [Allowlist log fields](../src/python_backend_guidance/guides/allowlist-log-fields.md)
- [Correlate request logs](../src/python_backend_guidance/guides/correlate-request-logs.md)
- [Bound metric labels](../src/python_backend_guidance/guides/bound-metric-labels.md)
- [Preserve error causes](../src/python_backend_guidance/guides/preserve-error-causes.md)
- [Separate health probes](../src/python_backend_guidance/guides/separate-health-probes.md)

## Files and subprocesses

- [Avoid shell interpolation](../src/python_backend_guidance/guides/avoid-shell-interpolation.md)
- [Bound subprocess resources](../src/python_backend_guidance/guides/bound-subprocess-resources.md)
- [Stream large files](../src/python_backend_guidance/guides/stream-large-files.md)
- [Replace files atomically](../src/python_backend_guidance/guides/replace-files-atomically.md)
- [Own temporary files](../src/python_backend_guidance/guides/own-temporary-files.md)

## Configuration and lifecycle

- [Validate startup configuration](../src/python_backend_guidance/guides/validate-startup-configuration.md)
- [Own resource lifetimes](../src/python_backend_guidance/guides/own-resource-lifetimes.md)
- [Unwind partial startup](../src/python_backend_guidance/guides/unwind-partial-startup.md)
- [Scope process resources](../src/python_backend_guidance/guides/scope-process-resources.md)
- [Serialize migration runners](../src/python_backend_guidance/guides/serialize-migration-runners.md)
