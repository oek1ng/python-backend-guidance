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
