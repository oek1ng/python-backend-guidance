---
name: python-backend-guidance
description: Find framework-independent Python 3.12+ backend guidance with tested examples. Use for concurrency, reliability, HTTP clients, database correctness and performance, messaging, caching, input contracts, authorization, observability, files, subprocesses, configuration and resource lifecycles. Check each recipe's runtime, library and service requirements.
---

# Python Backend Guidance

Consult the local CLI before implementing a covered backend capability.
The catalog contains 60 draft guides across 12 backend areas. Examples have
behavioral checks; independent technical review and agent uplift are separate evidence.

## Workflow

1. Read the project's instructions, Python requirements, dependencies, and
   concurrency runtime. Respect existing choices; do not migrate a project to a
   different framework, runtime, or Python version to follow a guide.
2. Search using one focused English capability:

   ```sh
   python-backend-guidance search "bounded async concurrency" --python 3.12 --runtime asyncio
   ```

   Search is local keyword matching, not semantic search. Judge returned
   descriptions; if necessary, rephrase once. An empty or irrelevant result
    does not establish useful coverage. Inspect `list` if necessary rather than
    applying an unrelated guide.
3. Retrieve matching IDs:

   ```sh
   python-backend-guidance retrieve bound-concurrent-work --python 3.12 --runtime asyncio
   ```

   Supply the project's actual constraints, not the CLI interpreter's version.
   Omit an unknown constraint and inspect the metadata; never guess it to obtain a
    match. Use `python-backend-guidance list` for the coverage inventory. `sync`
    identifies synchronous recipes; `any` has no concurrency-runtime requirement.
4. Check compatibility metadata and conditions before applying a recommendation.
   Draft status means behavioral examples exist, not that agent uplift has been
   demonstrated. If the project's Python version or runtime is incompatible,
   explain the mismatch rather than silently upgrading it.
5. Implement only what the task needs. Verify observable behavior, including
   applicable error and cancellation paths. Do not require the exact reference
   implementation if another design satisfies the same constraints.
6. Briefly mention which guide informed a non-obvious decision and what was
    actually verified.

Useful focused queries include `PostgreSQL lost updates`, `transactional outbox`,
`tenant scoped cache key`, `JWT token signature verification`, and
`subprocess timeout output limit`. Search one capability at a time.

## Typing when adapting examples

Use complete Python 3.12+ annotations: preserve input/result relationships with
PEP 695 generics, use `Protocol` for borrowed capabilities and `TypedDict` for
structured records. Prefer stdlib `typing`, ordinary imports, and narrowly quoted
forward references. Avoid `typing_extensions`, postponed annotations via
`from __future__ import annotations`, and `if TYPE_CHECKING`.

Validate untrusted boundary data before narrowing it. Do not replace meaningful
types with `Any`, broad `object`, blanket casts, or suppressed diagnostics.
Keep casts local to a justified boundary, such as a known SQL projection.
Check types and observable behavior: neither substitutes for the other.
This repository uses Pyrefly's `all` preset; respect the consuming project's
checker and supported Python version.

Database and broker claims require integration checks with the declared service.
Read example prerequisites and limits before adapting snippets; a source link or
passing local example is not a complete production guarantee.

If the CLI is unavailable, say so. Do not claim to have consulted it, invent
guides, install software, or fetch and execute remote code without permission.
