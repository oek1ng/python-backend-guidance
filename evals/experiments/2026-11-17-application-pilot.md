# Application-workflow research pilot

This is an internally authored exploratory comparison, **not** independent
evidence that guides improve coding-agent quality. Unlike the earlier
[direct-guide pilot](2026-11-16-sol-pilot.md), this experiment includes the
installed skill and local search/retrieve workflow. Its fixtures are small
synthetic applications, not independently selected existing projects; this
deviates from the stronger
[application-level protocol](application-workflow-protocol.md). The same author
created the tasks, references and checks. No independent review took place.

## Design

- Three tasks with two repeats in each of three conditions: 18 scheduled
  trials, paired by task and repeat. `inventory` (bounded async persistence)
  and `money` (decimal invoice totals) have relevant catalog guides. `tax`
  (selection from a supplied tax-rate table) is outside catalog coverage.
- Conditions: **baseline** gets no catalog access; **direct** gets the full
  preselected applicable guide where one exists; **workflow** gets the frozen
  skill and the installed CLI, but no preselected guide. For `tax`, baseline
  and direct receive the same guidance placeholder; only the workflow has
  access to search. The direct arm is an oracle-guide condition, not a search
  condition.
- Each task starts from the same defective `solution.py` in all conditions,
  with the same task contract, prompt, Python 3.12+ target, dependencies,
  `openai/gpt-6.1-sol#medium` model and OpenCode 2.3.0. The authoring agent
  can read its task, guidance/skill placeholders and source, and edit only
  `solution.py`; the workflow additionally permits narrowly scoped CLI
  search/list/retrieve commands. No test feedback or repair round is provided.
  Ten model steps and 180 seconds per run. Order was randomized with seed
  `20261117`.
- Separate grading uses Python 3.12.16 in a read-only Docker container with
  no network, unprivileged user, dropped capabilities, one CPU, 512 MiB RAM,
  64-process limit and a 45-second outer timeout. Image:
  `sha256:55abbe5e2b9b5b9a21645a4ce9d671d39aebc4c0150738c2a0fd147376a85ee5`.
  Before model calls, the `inventory`, `money` and `tax` references passed
  respectively 4, 6 and 4 checks in that container; each defective base
  failed. The authored checks are limited and not a proof of production
  correctness.

The inputs and order are hashed in the manifest. A recorder-only amendment
after the first trial is documented in `recorder-amendment.json`: an API call
successfully archived the session but returned an empty body, which crashed
the initial recorder after grading. That trial was reconstructed from its
saved solution and sanitized session export without rerunning the agent. Its
precise process wall time and exit code were lost; session busy-to-idle time
is reported instead. No task, guide, prompt, agent config, budget or grader
changed.

## Results

All 18 approved trials completed without agent or grader timeouts. Every
assistant step used the selected model and variant. Each candidate passed its
entire contract: **18/18** across all arms, **84/84** individual checks. No
unsuccessful trial was replaced. In each of the six task/repeat pairs, all
three conditions passed: the observed paired correctness differences were
**zero**, with no discordant pair. This ceiling does not establish equivalent
performance or an improvement from the guides.

| Outcome | Baseline | Direct guide | Skill + search |
| --- | ---: | ---: | ---: |
| Whole contracts passed | 6/6 | 6/6 | 6/6 |
| Individual checks passed | 28/28 | 28/28 | 28/28 |
| Mean elapsed time | 39.970 s | 27.396 s* | 39.560 s |
| Median elapsed time | 29.566 s | 24.702 s* | 39.080 s |
| Reported input tokens | 22,557 | 30,458 | 64,189 |
| Reported output tokens | 4,159 | 3,385 | 4,098 |
| Reported reasoning tokens | 2,746 | 1,015 | 789 |
| Reported cache-read tokens | 33,024 | 39,424 | 84,480 |

Cache-write tokens were reported as zero in all arms. Token fields are
separate counters, not an estimated bill. Reported cost was zero, but provider
prices are unavailable: actual monetary cost is **unknown**.

*One direct-guide trial has only session busy-to-idle time, not the same
process-wall-clock measurement as the other 17. Provider load, cache effects
and the tiny sample also prevent a meaningful latency comparison.*

Each task had 2/2 passes in every arm. For the two covered tasks, the workflow
searched and retrieved the matching guide in all **4/4** attempts:
`inventory` selected `bound-concurrent-work` twice and `money` selected
`quantize-money` twice. Each successful query/retrieval supplied the target
Python version and runtime. The workflow on the out-of-coverage `tax` task
did **not** establish a clean refusal: one run searched for configured integer
validation and retrieved the related generic `validate-boundary-data` guide,
not tax-rate guidance. In the other run, a compound `command -v ... && search`
was denied by the shell permission rule before search ran. It still solved the
task without a retrieved guide.

Across all trials there were eight permission-denied tool calls: six attempted
directory reads and two shell commands. One of those shell denials prevented
the tax search; another was an attempted `cat` outside the allowlist. There
were no observed agent exit failures or grader infrastructure failures. The
first trial was recovered after a **recorder** failure, as described above; its exact
process exit code is unobserved, while the saved session outcome is
`succeeded`. The maximum observed model-step count was eight.

## Evidence

The [evidence archive](2026-11-17-application-pilot.tar.gz) contains the
manifest, Docker calibration, hashed input sources and wheel, all candidate
solutions, per-trial results and sanitized transcripts. Its SHA256 is
`ed7f25445b79aa09fbb34c49ce1a38012d7bdccd4b59d8a16d42d796e766ad5f`.
Raw event streams are excluded. The original local workspace remains under
`/tmp/opencode/pbg-app-pilot-20261117-01/`.

Two exact runner versions, one for trial 1 and one for trials 2–18, are in the
archive and match the recorded hashes in `recorder-amendment.json`. A subsequent
type-check-only edit to the repository runner changed its source hash *after*
all trials; the frozen manifest deliberately continues to identify the
archived trial-time version rather than pretending that the edited checkout
was used during authoring.

## Interpretation and limits

Two repeats per task do not constitute independent replications. With three
internally authored synthetic tasks and no discordant outcomes, no useful
confidence interval for general agent uplift follows from these results.
The checks may miss important defects. Guide access, local search quality and
model behavior are confounded with prompt interpretation and uncontrollable
provider/cache load. The separate
[unguided report-capture discovery](2026-11-17-report-capture-discovery.md)
also found no baseline failure in its two attempts; it did not include a
guided comparison. Avoid claims of generalizable uplift or comparative
latency superiority from either exploratory experiment.
