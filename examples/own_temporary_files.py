"""File adapter: own and clean the workspace for one borrowed operation."""

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory


def with_workspace[T](operation: Callable[[Path], T]) -> T:
    with TemporaryDirectory(prefix="backend-") as directory:
        return operation(Path(directory))
