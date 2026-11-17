# Local retrieval and its limits

Search is model-independent and makes no network calls. It does not require a
selected agent, provider, model, budget, or embedding download.

## Ranking

1. Normalize English case, discard common request words and generic runtime
   words, and apply limited plural normalization.
2. Match against guide IDs, tags, titles, descriptions, and explicit aliases.
3. Require at least two meaningful metadata matches for a multi-term query, and
   coverage of at least half its meaningful terms. A one-term query requires one
   metadata match.
4. Rank by the number of query terms covered in capability metadata, then by
   weighted metadata matches. Relevant prose breaks score ties, then IDs provide
   deterministic ordering.

Coverage comes first so repeated generic words such as "worker pool" cannot
outvote the more specific "parallel worker pool" capability. The admission
threshold remains unchanged; this is still lexical ranking.

These are lexical heuristics, not semantic understanding or calibrated confidence.
Aliases are author-maintained descriptions of covered capabilities, not hidden
per-query answers or a list of unsupported topics.

Example code, source URLs, and exclusion prose cannot admit a result by themselves.
A guide mentioning a database transaction only to disclaim rollback guarantees
should not be retrieved as transaction guidance.

Use focused English capability queries rather than complete application prompts.
Inspect descriptions and requirements, and rephrase once when needed. Query
normalization does not handle every grammatical variation; returning no result
is preferable to claiming unrelated coverage. Constraints still need checking.

## Seed benchmark

Run the hand-authored retrieval corpus without a coding agent:

```sh
uv run python -m evals.search --split development
uv run python -m evals.search --split validation --check
```

`--output <new-file.json>` records a report without overwriting an existing file.
Reports include dataset and guide hashes, per-query results, and these metrics:

- Top-1 accuracy on supported queries.
- Hit@3 and mean reciprocal rank on supported queries.
- False-positive rate on queries outside current coverage.

The expanded corpus contains **172 queries**: 90 development (80 supported,
10 unsupported) and 82 validation (72 supported, 10 unsupported). Every guide
has at least one supported query in each split. Labels can allow multiple relevant guides.
The seed regression gate requires Top-1 >=90% and unsupported false positives
<=10%; `--check` exits 1 if either target is missed.

**This is a small regression corpus, not independent evidence of general search
quality.** It was authored alongside the guides. Development and validation sets
are separate, but must not be presented as a large blind external evaluation.
Development queries intentionally include canonical capability terminology and
aliases; their high score is primarily a coverage smoke check.

## Expanded-catalog measurement

With 60 guides, development produced 80/80 correct first results and 0/10
unsupported matches. The first expanded validation run produced **70/72 Top-1
(97.2%)**, Hit@3 70/72, and **1/10 false positives (10%)**.

Retained limitations:

- "avoid retrying permanent errors" returned nothing (also missed by the original
  three-guide catalog).
- "keep old writers working during schema rollout" returned nothing.
- "choose database isolation level" incorrectly returned tenant/object access
  guides. The catalog has a serializable retry recipe, not an isolation-level
  selection guide.

The ranking was changed after a development query exposed confusion between
database connection pools and parallel worker pools. These validation failures
were not subsequently used to retune the reported result.

## Dataset evolution

The original corpus had 26 development and 18 validation queries. Its three-guide
measurement was 11/12 Top-1 and 0/6 unsupported matches. Eight previously negative
labels now point to newly covered capabilities (transactions, HTTP client lifetime,
authorization, response limits, lost updates, JWTs, file confinement and cache
expiry). The remaining original queries are retained, and new queries cover all
57 additions plus new unsupported topics.

The old and expanded metrics are therefore **not a same-dataset improvement
comparison**. A relevant general recipe also does not imply library-specific
support: for example a transaction query mentioning SQLAlchemy may retrieve a
Psycopg example whose applicability must be checked.

Before a v1.0 quality claim, independently review labels, add genuinely external
queries, and repeat the measurement. Ten negative queries give only a coarse
false-positive estimate; passing the regression gate is not a confidence bound.
