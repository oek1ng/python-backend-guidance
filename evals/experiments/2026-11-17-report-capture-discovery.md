# Unguided report-capture discovery: negative result

The purpose of this **exploratory, internally authored** case was to find an
application bug that an agent would fail to fix without the catalog. It did
**not** find one. No guided runs were requested or performed; these results
cannot measure the effect of a guide.

## Frozen case and budget

The application captures output from a trusted POSIX report generator. Its
defective implementation waits for all output before checking the byte limit
and kills only the main process, not a helper that inherited its output stream.
The task specifies prompt overflow rejection, timeout and cancellation cleanup,
and no surviving owned helpers without naming an implementation technique or
guide. Both authoring workspaces started with byte-identical `TASK.md`,
`solution.py` and `opencode.json`; neither contained the checks, a guide, or
the reference. Agent permissions denied shell, skills and external reads.

- Model: `openai/gpt-6.1-sol#medium`, OpenCode 2.3.0, maximum 10 model steps
  and 180 seconds per run; two sequential baseline repeats with no feedback
  between runs.
- Python 3.12+ target, stdlib asyncio and POSIX process APIs, no third-party
  services. The related catalog guide is `bound-subprocess-resources`
  (Python >=3.12, asyncio, POSIX process groups), but it was **not provided**.
- Separate checks ran on Python 3.12.16 in the read-only, unprivileged,
  network-disabled Docker image
  `sha256:55abbe5e2b9b5b9a21645a4ce9d671d39aebc4c0150738c2a0fd147376a85ee5`,
  with one CPU, 512 MiB RAM, 64-process limit and 45-second outer timeout.
  Before either agent call, the reference passed 6/6 checks and the original
  defective version failed three: delayed overflow, helper surviving parent
  cancellation, and helper surviving after the leader exited. The checks
  remained unchanged after seeing the agent's output.

## Observations

| Unguided repeat | Contract | Model steps | Elapsed | Input / output / reasoning | Cache read / write |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 6/6 passed | 3 | 59.564 s | 2,801 / 833 / 939 | 5,888 / 0 |
| 2 | 6/6 passed | 4 | 74.740 s | 4,718 / 865 / 1,066 | 6,784 / 0 |

Both agents exited successfully within budget. Each attempted to load the
`python-backend-guidance` skill, but the permission denied it; neither
retrieved guide content. There were no grader failures or replacement trials.
The reported cost was zero, but provider pricing is unavailable, so the actual
cost is **unknown**. Token categories are reported separately, not summed into
a bill.

The two solutions both implemented early output rejection and group cleanup;
they also introduced cleanup around cancellation during process creation.
That latter behavior was **not independently checked** and is not a claim of
production safety. Six internally authored checks cannot prove correctness
outside their stated scenarios.

The hashed manifest, calibration, input files, solutions, sanitized transcripts
and per-run results are in the
[evidence bundle](2026-11-17-report-capture-discovery.tar.gz), SHA256
`d291775783e7b8fb7d8bee2e87ee59145e4db023aa260f30324dab7f020c68b2`.
Raw agent event streams are excluded. The original workspace is
`/tmp/opencode/pbg-report-capture-discovery-20261117-01/`. This is a
**discovery failure**, not evidence against the usefulness of guidance in
general. Selecting only tasks on which baseline fails would itself bias a
later efficacy estimate; any such discoveries require a separate untouched
confirmation set and independent review of the graders.
