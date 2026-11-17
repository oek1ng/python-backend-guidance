"""Small, offline search/retrieve interface for coding agents."""

import argparse
import json
import sys
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Literal, TypedDict

from .catalog import load_guides, search_guides
from .guide import GuideError, python_version


class Arguments(argparse.Namespace):
    command: Literal["search", "retrieve", "list", "export-skill"] = "list"
    query: str = ""
    limit: int = 5
    id: str = ""
    output: Path | None = None
    python: tuple[int, int] | None = None
    runtime: str | None = None


class SearchResult(TypedDict):
    id: str
    title: str
    description: str
    python: str
    runtime: str
    status: Literal["draft", "reviewed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python-backend-guidance")
    _ = parser.add_argument(
        "--version",
        action="version",
        version=version("python-backend-guidance"),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Find guides with local keyword search")
    _ = search.add_argument("query", help="A focused English query")
    _ = search.add_argument("--limit", type=int, default=5)
    retrieve = commands.add_parser("retrieve", help="Print a guide as Markdown")
    _ = retrieve.add_argument("id", help="An ID returned by search")
    listing = commands.add_parser("list", help="List available guides")
    export = commands.add_parser(
        "export-skill", help="Print or safely export the skill"
    )
    _ = export.add_argument(
        "--output", type=Path, help="Create this file; never overwrite an existing path"
    )
    for command in (search, retrieve, listing):
        _ = command.add_argument(
            "--python", type=python_version, help="Target project version, e.g. 3.12"
        )
        _ = command.add_argument(
            "--runtime", help="Target runtime, e.g. asyncio or trio"
        )
    args = parser.parse_args(argv, namespace=Arguments())

    if args.command == "export-skill":
        try:
            # Metadata locates wheel data even when Python modules are editable.
            skill = distribution("python-backend-guidance").locate_file(
                "python_backend_guidance/SKILL.md"
            )
            content = Path(str(skill)).read_text(encoding="utf-8")
            if args.output is not None:
                output = args.output.expanduser()
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("x", encoding="utf-8") as destination:
                    _ = destination.write(content)
                print(f"Skill exported to {output}", file=sys.stderr)
            else:
                print(content, end="")
            return 0
        except OSError as error:
            print(f"Cannot export skill: {error}", file=sys.stderr)
            return 1

    if args.command == "search":
        if args.query.strip() == "":
            parser.error("query must not be blank")
        if args.limit < 1:
            parser.error("--limit must be positive")
    try:
        guides = load_guides()
    except GuideError as error:
        print(f"Invalid catalog: {error}", file=sys.stderr)
        return 1

    if args.command in {"search", "list"}:
        applicable = [
            guide for guide in guides if guide.applies_to(args.python, args.runtime)
        ]
        matches = (
            search_guides(args.query, applicable, limit=args.limit)
            if args.command == "search"
            else applicable
        )
        results: list[SearchResult] = [
            {
                "id": guide.id,
                "title": guide.title,
                "description": guide.description,
                "python": guide.python,
                "runtime": guide.runtime,
                "status": guide.status,
            }
            for guide in matches
        ]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for guide in guides:
        if guide.id == args.id:
            if not guide.applies_to(args.python, args.runtime):
                print(
                    f"Incompatible guide: {guide.id} requires Python "
                    f"{guide.python}, runtime {guide.runtime}",
                    file=sys.stderr,
                )
                return 1
            print(guide.content, end="")
            return 0
    print(f"Guide not found: {args.id}", file=sys.stderr)
    return 1
