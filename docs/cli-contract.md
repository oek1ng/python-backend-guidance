# CLI contract, version 1 candidate

These interfaces are exercised during Alpha. They are intended to stabilize for
v1.0; package version and guide-content hashes identify the exact behavior used
in an evaluation. This is not a Python-library API stability promise.

## Commands

```sh
python-backend-guidance --version
python-backend-guidance list
python-backend-guidance search "bounded concurrent work" --limit 3
python-backend-guidance retrieve bound-concurrent-work
python-backend-guidance export-skill
python-backend-guidance export-skill --output ./chosen-skills/python-backend-guidance/SKILL.md
```

`list`, `search`, and `retrieve` accept `--python MAJOR.MINOR` and `--runtime NAME`.
These describe the **target project**, not the CLI's host interpreter.

Without constraints, guides are not assumed compatible with the project: their
requirements remain visible and must be checked. With explicit constraints,
search/list omit incompatible guides; retrieve rejects an incompatible ID rather
than quietly returning another guide.

The Alpha catalog includes draft guides. Every result explicitly exposes status;
draft does not mean independently reviewed or agent-evaluated. The default policy
for a reviewed public catalog will be decided before v1.0.

## Output

Search and list write a JSON array to stdout. Results contain:

```json
[
  {
    "id": "bound-concurrent-work",
    "title": "Bound concurrent work",
    "description": "Process a large async input stream with bounded concurrency and backpressure.",
    "python": ">=3.12",
    "runtime": "asyncio",
    "status": "draft"
  }
]
```

Consumers should tolerate additive fields. Search order is deterministic:
query coverage in capability metadata, weighted metadata, prose tie-breaking,
then ID. List order is by ID.
There are no confidence probabilities or claims of semantic understanding.
See [retrieval](retrieval.md) for admission rules and measurements.

No search match is `[]`, not an error. Retrieve writes the complete Markdown
unchanged, including metadata. Diagnostic messages go to stderr, not JSON stdout.
Catalog validation fails before partial results are printed.

`export-skill` prints the packaged skill to stdout, or creates an explicitly
selected `--output` file and any missing parent directories. File export writes
only a confirmation to stderr. It never overwrites an existing file or follows an
existing output symlink, and never selects an agent-specific path or configuration.
The wheel includes the skill; a repository checkout is not needed to export it.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Successful search/list/retrieval, including an empty result set |
| `1` | Missing/incompatible guide, invalid catalog, or skill export failure |
| `2` | CLI usage error |

The CLI makes no network requests and never executes guide examples. Version,
runtime, and library choices are not changed on the user's behalf. Metadata
filters do not validate service or library requirements.
