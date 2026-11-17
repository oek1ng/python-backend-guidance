"""Versioned guide metadata, without importing or executing example code."""

import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from typing import Literal, Never, cast
from urllib.parse import urlsplit


class GuideError(ValueError):
    """An invalid guide or unsupported metadata schema."""


def python_version(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError("Python version must be MAJOR.MINOR, for example 3.12")
    return int(match[1]), int(match[2])


@dataclass(frozen=True)
class Source:
    url: str
    checked: date


@dataclass(frozen=True)
class Guide:
    id: str
    title: str
    description: str
    python: str
    runtime: str
    tags: tuple[str, ...]
    status: Literal["draft", "reviewed"]
    example: str
    sources: tuple[Source, ...]
    libraries: tuple[tuple[str, str], ...]
    services: tuple[str, ...]
    content: str
    aliases: tuple[str, ...] = ()

    @property
    def minimum_python(self) -> tuple[int, int]:
        return python_version(self.python[2:])

    def applies_to(
        self,
        project_python: tuple[int, int] | None = None,
        runtime: str | None = None,
    ) -> bool:
        return (project_python is None or project_python >= self.minimum_python) and (
            runtime is None or self.runtime in {"any", runtime}
        )


def parse_guide(content: str, *, filename: str) -> Guide:
    def fail(message: str) -> Never:
        raise GuideError(f"{filename}: {message}")

    def strings(value: object, message: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            fail(message)
        result: list[str] = []
        for item in cast(list[object], value):
            if not isinstance(item, str) or item.strip() == "":
                fail(message)
            result.append(item)
        return tuple(result)

    if not content.startswith("+++\n"):
        fail("missing TOML front matter")
    header, closing, _body = content[4:].partition("\n+++\n")
    if closing == "":
        fail("missing closing +++ delimiter")
    try:
        metadata: dict[str, object] = tomllib.loads(header)
    except tomllib.TOMLDecodeError as error:
        raise GuideError(f"{filename}: invalid TOML: {error}") from error

    if (
        type(metadata.get("schema_version")) is not int
        or metadata["schema_version"] != 1
    ):
        fail("schema_version must be 1")
    fields: dict[str, str] = {}
    for field in (
        "id",
        "title",
        "description",
        "python",
        "runtime",
        "status",
        "example",
    ):
        value = metadata.get(field)
        if not isinstance(value, str) or value.strip() == "":
            fail(f"{field} must be a nonempty string")
        fields[field] = value
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["id"]) is None:
        fail("id must be a lowercase hyphenated slug")
    if filename != f"{fields['id']}.md":
        fail("id must match the filename")
    if re.fullmatch(r">=\d+\.\d+", fields["python"]) is None:
        fail("python must be a minimum such as >=3.12")
    if python_version(fields["python"][2:]) < (3, 12):
        fail("guides require at least Python 3.12")

    tags = strings(
        metadata.get("tags"), "tags must be a nonempty array of nonempty strings"
    )
    if len(tags) == 0:
        fail("tags must be a nonempty array of nonempty strings")
    status = fields["status"]
    if status != "draft" and status != "reviewed":
        fail("status must be draft or reviewed")
    if status == "reviewed":
        reviewer = metadata.get("reviewed_by")
        if not isinstance(reviewer, str) or reviewer.strip() == "":
            fail("reviewed_by must identify the reviewer")
        if type(metadata.get("reviewed_on")) is not date:
            fail("reviewed_on must be a TOML date")

    example = PurePosixPath(fields["example"])
    if (
        example.is_absolute()
        or len(example.parts) == 0
        or example.parts[0] != "examples"
        or ".." in example.parts
        or "\\" in fields["example"]
        or example.suffix != ".py"
    ):
        fail("example must be a relative Python path under examples/")

    source_data = metadata.get("sources")
    if not isinstance(source_data, list) or len(source_data) == 0:
        fail("sources must be a nonempty array of tables")
    sources: list[Source] = []
    for raw_source in cast(list[object], source_data):
        if not isinstance(raw_source, dict):
            fail("each source requires a url")
        source = cast(dict[object, object], raw_source)
        source_url = source.get("url")
        if not isinstance(source_url, str):
            fail("each source requires a url")
        try:
            url = urlsplit(source_url)
        except ValueError as error:
            raise GuideError(f"{filename}: invalid source url") from error
        if (
            url.scheme not in {"http", "https"}
            or url.hostname is None
            or url.hostname == ""
            or url.username is not None
            or url.password is not None
        ):
            fail("source url must be an HTTP(S) URL without credentials")
        checked = source.get("checked")
        if type(checked) is not date:
            fail("source checked must be a TOML date")
        sources.append(Source(url=source_url, checked=checked))

    raw_libraries = metadata.get("libraries", {})
    if not isinstance(raw_libraries, dict):
        fail("libraries must map names to nonempty version requirements")
    libraries: dict[str, str] = {}
    for name, constraint in cast(dict[object, object], raw_libraries).items():
        if (
            not isinstance(name, str)
            or name.strip() == ""
            or not isinstance(constraint, str)
            or constraint.strip() == ""
        ):
            fail("libraries must map names to nonempty version requirements")
        libraries[name] = constraint
    optional: dict[str, tuple[str, ...]] = {}
    for field in ("services", "aliases"):
        optional[field] = strings(
            metadata.get(field, []), f"{field} must be an array of nonempty strings"
        )

    return Guide(
        id=fields["id"],
        title=fields["title"],
        description=fields["description"],
        python=fields["python"],
        runtime=fields["runtime"],
        tags=tags,
        status=status,
        example=fields["example"],
        sources=tuple(sources),
        libraries=tuple(sorted(libraries.items())),
        services=optional["services"],
        content=content,
        aliases=optional["aliases"],
    )
