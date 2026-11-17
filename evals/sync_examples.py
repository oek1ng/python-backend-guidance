"""Refresh guide reference blocks from their declared executable examples."""

from pathlib import Path

from python_backend_guidance.catalog import load_guides

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for guide in load_guides():
        path = ROOT / "src/python_backend_guidance/guides" / f"{guide.id}.md"
        content = path.read_text(encoding="utf-8")
        before, marker, remainder = content.partition("```python\n")
        _, closing, after = remainder.partition("\n```")
        if marker == "" or closing == "":
            raise ValueError(f"{path}: missing complete Python reference block")
        example = (ROOT / guide.example).read_text(encoding="utf-8").rstrip()
        updated = before + marker + example + closing + after
        if updated != content:
            _ = path.write_text(updated, encoding="utf-8")
            print(guide.id)


if __name__ == "__main__":
    main()
