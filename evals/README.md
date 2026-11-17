# Agent evaluations

This directory contains 60 task contracts, executable solution grading, and
reference/defect calibration. The standard grader does **not** invoke coding agents.
An externally orchestrated [12-run direct-guide pilot](experiments/2026-11-16-sol-pilot.md)
records equal correctness in both groups and exploratory timing/token measurements.
The [18-run application-workflow pilot](experiments/2026-11-17-application-pilot.md)
passed every check in all three conditions; a
[two-run unguided discovery](experiments/2026-11-17-report-capture-discovery.md)
also found no baseline failure. These internally authored tasks do not establish
guided-versus-unguided uplift. Independent review and broader agent trials
remain release work.

## Run locally

From a development checkout with dev dependencies installed:

Configure the disposable service endpoints in
[integration testing](../docs/integration-testing.md) for full calibration.

```sh
uv run python -m evals.run calibrate
uv run python -m evals.run grade \
  --task apply-operation-deadline \
  --solution examples/apply_operation_deadline.py \
  --allow-code-execution
```

Add `--output <new-file.json>` to save a report; existing reports are never
overwritten. Exit 0 means grading/calibration passed, 1 means failure, and 2 means
invalid arguments or missing execution permission.

`tasks.toml` maps each guide to its public interface, reference module, tests,
task description, and intentionally defective solution/check. Calibration runs
the full contract for every reference, alternative, and defect. References and
alternatives must pass every check. A defect must fail exactly `must_fail` plus
any explicitly declared `related_failures`; all other checks must pass, with the
same collected check names and counts as the reference. Timeouts, skipped checks,
collection/setup errors, missing checks, and unrelated failures cannot pass
calibration. Valid alternatives exercise queue-free bounded concurrency and a
singleflight close that drains loaders instead of cancelling them.
The baseline 60 defective implementations live in `candidates/defects.py`; additional
single-mutation candidates live alongside it. JWT calibration separately checks
signature verification, issuer, audience and algorithm policy. Additional candidates
exercise subprocess group cleanup, shared-loader retry/join, transaction commit and
delivery acknowledgement. Valid alternatives live in `candidates/alternatives.py`.
All task descriptions share `contracts.md`. Run tools as modules from the repository
root.

Each candidate documents one mutation and preserves unrelated validation,
results, and resource ownership. `related_failures` is for multiple observations
of that same mutation: premature NOT NULL rejects old rows and old writers;
missing tenant scoping breaks both cross-tenant reads and missing-tenant denial;
logging headers leaks both known credentials and unrecognized fields. Do not
expand this list to accept unrelated bugs. An intentionally unused public
parameter must be explained by the mutation itself.

The same pytest contract tests grade reference and candidate modules through an
implementation fixture. There is no second copy of the graders to drift from the
reference checks. Checks accept tighter read-ahead limits and direct or grouped
ordinary exceptions; they do not require `Queue` or the reference algorithm.
Retry arithmetic uses declared random/timer seams; real asyncio remains in
timeout, lifecycle, and cancellation checks.

Reports include outcomes, interpreter/tool versions, and hashes for the solution,
guide, public task contract, checks, fixtures, runner, registry, helper modules and
dependency lockfile. The POSIX grader retains at most 16,000 output bytes and
terminates its owned process group on completion or timeout. Pytest's automatic
stdout/stderr capture is disabled so normal candidate output streams through
that limit; exceptionally large test-generated JUnit XML, traceback data, and
descendants that escape the process group still require an external sandbox's
resource limits. A subprocess timeout or grader infrastructure error is explicit, never
a passing result. CI retains evaluation reports as artifacts for 14 days; inspect
them before sharing because even truncated logs can contain private data.

## Tasks

See [all 60 public contracts](contracts.md): concurrency, databases, messaging,
caching, HTTP/security, observability, files and resource lifecycle.

The shared test files select contracts by marker and `--task`. Reference modules
and plausible defective variants are registered individually for every guide.
Service-dependent tasks are real integration tests; missing endpoints cause skips
and therefore a nonpassing calibration, rather than fabricated mock evidence.

## Security boundary

**This runner is not a security sandbox.** Grading imports and executes the supplied
module. The subprocess receives a reduced environment and a timeout, but can still
access files and the network, start other processes, or alter test files.
Only run trusted solutions locally. For untrusted generated code, configure an
external sandbox with filesystem/network isolation and resource limits first.
The permission flag is acknowledgement, not isolation.
The two explicit disposable-service endpoint variables are forwarded to the child.
Inspect reports before publishing: solution output can contain private data, and
diagnostic logs can include local filesystem paths.

Never execute untrusted pull-request code with repository secrets. Agent output
must not be allowed to change hidden graders. Do not treat this local calibration
tool as a hardened evaluator for adversarial submissions.

## Before claiming agent uplift

1. Independently review the task contracts and graders.
2. Supply identical isolated base projects, permissions, prompts, and budgets
   across guided and unguided trials.
3. Pin the agent/model and guide version; record tool failures separately.
4. Run repeated paired trials, including tasks outside the catalog's coverage.
5. Report correctness, uncertainty, retrieval behavior, and token/time costs.

Measure direct-guide assistance separately from the complete skill/search/retrieve
workflow. No model credentials, model calls, or automatic spending are part of
this Alpha runner.
