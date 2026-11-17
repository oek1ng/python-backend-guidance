from pathlib import Path

import pytest

from python_backend_guidance.cli import main

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "skills/python-backend-guidance/SKILL.md"


def test_export_to_stdout_matches_the_canonical_skill(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(["export-skill"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.out == CANONICAL.read_text(encoding="utf-8")
    assert captured.err == ""


def test_export_creates_only_the_explicitly_selected_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "chosen-location" / "SKILL.md"

    result = main(["export-skill", "--output", str(output)])

    captured = capsys.readouterr()
    assert result == 0
    assert output.read_text(encoding="utf-8") == CANONICAL.read_text(encoding="utf-8")
    assert captured.out == ""
    assert "exported" in captured.err
    assert sorted(path.name for path in tmp_path.iterdir()) == ["chosen-location"]


def test_export_does_not_overwrite_an_existing_user_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "SKILL.md"
    _ = output.write_text("user-owned instructions", encoding="utf-8")

    result = main(["export-skill", "--output", str(output)])

    captured = capsys.readouterr()
    assert result == 1
    assert output.read_text(encoding="utf-8") == "user-owned instructions"
    assert captured.out == ""
    assert "Cannot export skill" in captured.err
    assert "Traceback" not in captured.err


def test_export_does_not_follow_an_existing_output_symlink(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "must-not-be-created.md"
    output = tmp_path / "SKILL.md"
    output.symlink_to(target)

    result = main(["export-skill", "--output", str(output)])

    assert result == 1
    assert output.is_symlink()
    assert not target.exists()
    assert "Cannot export skill" in capsys.readouterr().err
