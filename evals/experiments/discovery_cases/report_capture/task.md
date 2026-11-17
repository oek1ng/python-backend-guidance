# Report generator sometimes leaves a worker running

Fix `solution.py` in this small POSIX application. Keep its Python 3.12+
interface:

```python
async def capture_report(
    argv: Sequence[str], *, timeout_seconds: float, output_limit_bytes: int
) -> bytes: ...
```

`argv` invokes a **trusted** local report generator without a shell. Return
its complete stdout and stderr together as bytes on exit code zero. A nonzero
exit raises `RuntimeError`. The generator may start a non-daemonizing helper
that inherits its output stream, and the main process may exit before that
helper. The caller must never wait indefinitely for the stream to close.

Reject a nonpositive timeout or negative output limit with `ValueError`
*before starting the generator*. Reject output that exceeds the byte limit
as soon as that limit is exceeded, rather than waiting for process exit; the
generator may keep running after writing its output. A timeout raises
`TimeoutError`. On overflow, timeout, cancellation or another failure, do
not leave the started generator or its helpers running. Wait for the owned
main process to finish cleanup before returning or propagating the error.
No partial result may be returned on failure.

No support for daemonizing or deliberately detached helpers is requested.
Running this trusted tool is not a sandbox for untrusted programs. Python
3.12+ stdlib and POSIX process APIs only.
