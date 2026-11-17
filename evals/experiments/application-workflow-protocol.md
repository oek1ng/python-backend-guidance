# Application-level agent evaluation protocol

The 2026-11-16 direct-guide pilot reached a correctness ceiling. Do not repeat
its near-reference tasks and call the result evidence of agent uplift. This is
a protocol for a **new** experiment, not a report of completed trials.

## Prepare before model calls

1. Select existing small applications with pre-existing backend defects. Freeze
   an identical source snapshot per task and independently review the expected
   behavior, hidden checks and test-service setup. At least one task must be
   outside the catalog's coverage. Do not let an agent read or alter graders.
2. Define the same task prompt, edit scope, time/step budget, Python version and
   available dependencies for each condition. Do not copy a guide's reference
   implementation or ID into the prompt. Freeze the guide, skill and CLI version.
3. Record the OpenCode version, agent/model ID and variant, config/instructions
   hashes, seed, randomization order, sandbox image digest, and all input hashes.
   Record one run result even on timeout, tool error or missing solution. Never
   replace an unsuccessful run after seeing its result.
4. Grade generated code in a separate, read-only, network-disabled container
   with explicit CPU/memory/process/time limits. The local `evals.run` tool is
   **not** a sandbox. Only use disposable services for integration tasks.
   Inspect and redact diagnostic logs before sharing results.

## Conditions

Use paired repeated trials for each task with randomized condition order:

- **Baseline:** no guidance or catalog tools.
- **Direct guide:** supply a preselected applicable guide; this measures access
  to an oracle guide, not retrieval.
- **Workflow:** supply the installed skill and allow `search`, `list`, and
  `retrieve` on the frozen local catalog. Do not preload the applicable guide;
  record queries, returned IDs, compatibility checks, and refusals.

An out-of-coverage task tests whether the workflow avoids inventing coverage.
Keep authoring permissions identical except for the guidance interface and
keep model-call limits and budgets identical across arms.

## Report

Report per-condition contract pass rate, paired differences with uncertainty,
incorrect guide selections and out-of-coverage refusals, tool failures, elapsed
time, and separately accounted input/output/cache/reasoning tokens. Report
provider price as unknown if unavailable. Separate pilot findings from
conclusions about general agent performance. An internally authored/graded
experiment cannot count as independent technical review.
