# Python Backend Guidance

Framework-independent, verifiable Python backend guidance for coding agents.

**Expanded Alpha:** 60 draft guides across 12 backend areas, a local CLI,
an agent skill, and solution grading/calibration. Reference examples have behavioral tests;
a [small direct-guide agent pilot](evals/experiments/2026-11-16-sol-pilot.md) is recorded.
General agent-performance improvements have not been established. The package has
not been published to PyPI.

## Principles

- Prefer correctness, reliability, and security over novelty.
- State applicability, versions, ownership, and limitations explicitly.
- Respect the project's existing framework, runtime, and architecture.
- Present reference examples as Clean Architecture slices: independent policies,
  borrowed ports, and explicit adapters or composition roots where needed.
- Focus on concrete mistakes rather than repeating a Python textbook.
- Test behavior and measure agent outcomes before claiming effectiveness.

The project requires **Python 3.12+** throughout. CI covers Python 3.12, 3.13,
and 3.14. A guide using newer APIs must declare its stricter minimum.

All project Python code and reference snippets use modern, explicit typing,
checked with Pyrefly's `all` preset. See the [typing policy](docs/typing.md).

## Install from a checkout

```sh
uv tool install .
```

Or use `python -m pip install .` with Python 3.12+ in a suitable environment.

```sh
python-backend-guidance search "bounded async concurrency"
python-backend-guidance retrieve bound-concurrent-work
python-backend-guidance list
python-backend-guidance search "workflow deadline" --python 3.12 --runtime asyncio
```

Search/list return JSON with guide IDs, descriptions, requirements, and review status.
Retrieval prints the full Markdown guide, including compatibility metadata.
No matches produces `[]`; an unknown guide ID exits with status 1. Invalid CLI
arguments exit with status 2.

Explicit `--python` and `--runtime` values describe the target project; they are
never inferred from the CLI interpreter. Filters omit incompatible guides;
retrieval rejects explicit incompatibility. Other library/service requirements
still need inspection. See [the CLI contract](docs/cli-contract.md).

Search is deterministic English keyword matching with explicit aliases.
Query coverage ranks before weighted keyword frequency.
Capability metadata admits results; prose only breaks ranking ties. It is not
semantic search. See [retrieval behavior and the seed benchmark](docs/retrieval.md).
The installed CLI includes its guides and makes no network calls. There is no
telemetry, model download, API key, or runtime third-party dependency.
Installation may require network access to obtain build tools.

For reproducible agent runs, record the installed package version and checkout
revision rather than silently fetching the latest release for every query.

## Use with a coding agent

The skill is included in the installed package. Inspect it or export it to a
location you choose:

```sh
python-backend-guidance export-skill
python-backend-guidance export-skill --output ./chosen-skills/python-backend-guidance/SKILL.md
```

Replace that example directory with your agent's documented skill location.
Export refuses existing files and output symlinks; it does not silently change
user instructions or select an agent. No particular agent, model, or spending
budget is required or configured by the product.

The canonical source remains
[`skills/python-backend-guidance/SKILL.md`](skills/python-backend-guidance/SKILL.md).

The workflow is: inspect project constraints → search → retrieve applicable
guidance → implement → verify behavior. Do not load the whole catalog into every
task, apply unrelated guides, or change the framework to match an example.

## Current coverage

Browse the **[complete 60-guide catalog](docs/catalog.md)**:

| Area | Guides |
| --- | ---: |
| Concurrency and request context | 5 |
| Reliability, idempotency and shutdown | 5 |
| HTTP clients, streaming and TLS | 5 |
| Database correctness and write races | 5 |
| Query performance, pools and migrations | 5 |
| Messages, inbox/outbox and redelivery | 5 |
| Caches and distributed-state fencing | 5 |
| Input validation, timestamps and money | 5 |
| Authorization, tenant isolation and secure boundaries | 5 |
| Logging, metrics, errors and health probes | 5 |
| Files and subprocesses | 5 |
| Configuration and resource lifecycle | 5 |

Each guide has a runnable reference, reusable behavioral contract, deliberately
defective calibration candidate, sources and explicit limitations. All remain
`draft`: source inspection, tested examples, independent review and agent outcome
measurements are different evidence.

Recipes include runtime-independent logic, synchronous I/O and asyncio. Database
examples explicitly target PostgreSQL/Psycopg; broker adapters target RabbitMQ/Pika.
Framework-independent does not mean database- or runtime-independent.

```sh
python-backend-guidance search "PostgreSQL lost updates" --runtime sync
python-backend-guidance search "JWT required expiration issuer and audience"
python-backend-guidance retrieve transactional-outbox
```

## Develop

```sh
uv sync --locked --group dev --python 3.12
uv run --python 3.12 pytest
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format --check .
uv run --python 3.12 pyrefly check
uv run --python 3.12 python examples/bound_concurrent_work.py
uv run --python 3.12 python -m evals.run calibrate
uv run --python 3.12 python -m evals.search --split validation --check
uv build
```

For the full suite and calibration, start the disposable PostgreSQL/RabbitMQ
services and export the endpoints in [integration testing](docs/integration-testing.md).
Without them, service-dependent pytest checks are skipped and calibration cannot
pass. HTTP/TLS checks use local servers. CI runs all contracts on Linux.

Markdown files under `src/python_backend_guidance/guides/` are the content source
of truth and are included in wheels. TOML front matter uses `+++` delimiters so
the CLI can parse metadata with the standard library. The reference example also
lives under `examples/`; a test prevents the guide and executable copy drifting.

The skill has one canonical source and is copied into build artifacts. `uv`
tracks it as a build cache key. With another editable-install tool, reinstall the
package after changing the skill to refresh the packaged snapshot.

See [the versioned guide format](docs/guide-format.md),
[CONTRIBUTING.md](CONTRIBUTING.md) for contribution requirements, and
[evals/README.md](evals/README.md) for grading, security boundaries, and remaining
agent-evaluation work.

## Licensing

- Software, configuration, tests, and code snippets: [Apache-2.0](LICENSE).
- Documentation prose, guides, skill prose, and evaluation descriptions:
  [CC-BY-4.0](LICENSE-DOCS.md).

Inspired by the search/retrieve and evaluation approach of
[Modern Web Guidance](https://github.com/GoogleChrome/modern-web-guidance).
This is an independent project, not affiliated with or endorsed by its maintainers.
