+++
schema_version = 1
id = "avoid-shell-interpolation"
title = "Pass subprocess arguments without shell interpolation"
description = "Invoke a trusted executable with an argument vector so shell metacharacters remain literal input."
python = ">=3.12"
runtime = "sync"
tags = ["subprocess", "shell-injection", "arguments", "executables"]
aliases = ["shell command injection", "safe subprocess arguments"]
status = "draft"
example = "examples/avoid_shell_interpolation.py"
[[sources]]
url = "https://docs.python.org/3.12/library/subprocess.html"
checked = 2026-11-16
+++

# Pass subprocess arguments without shell interpolation

## When to use

Use when an external executable is genuinely needed. A suitable library call is
often simpler and avoids process-launch and argument-parsing concerns.

## Rules

1. Choose a trusted executable, preferably by absolute configured path.
2. Pass each argument as a separate sequence element.
3. Validate the tool's own option/value grammar, including leading hyphens.
4. Bound execution and output, and propagate nonzero status deliberately.

## Reference example

```python
"""Process adapter: run a trusted executable with an argument vector."""

import subprocess


def run_tool(executable: str, argument: str) -> str:
    return subprocess.run(
        [executable, argument],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout
```

## Guarantees and assumptions

No shell parses the argument. The chosen tool accepts one bounded literal value
and produces bounded output; otherwise use streaming output limits. Configuration
controls executable identity and environment.

## Pitfalls

`shell=True` with a formatted string permits shell injection. A safe argv still
allows option injection in tools that interpret a leading `-`; use their `--`
separator where supported. On Windows, batch files have additional shell behavior.

## Verification

Run `uv run pytest tests/test_backend_files.py --task avoid-shell-interpolation`.
The POSIX test tool echoes a metacharacter-containing argument literally and
reports nonzero exits.

## Sources

- [Python subprocess security considerations](https://docs.python.org/3.12/library/subprocess.html)
