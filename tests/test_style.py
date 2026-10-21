"""Keeps the code readable. A line too long to read at a glance fails the build, in the
Python and in the website's TypeScript alike, and no source file may grow into a catch-all."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAX_LINE = 110
MAX_FILE_LINES = 500
PYTHON = ("src/**/*.py", "tests/**/*.py", "animation/*.py")
WEBSITE = tuple(f"frontend/{folder}/**/*.{kind}"
                for folder in ("app", "components", "lib", "tests") for kind in ("ts", "tsx"))
SOURCES = sorted(path for pattern in PYTHON + WEBSITE for path in ROOT.glob(pattern))


@pytest.mark.parametrize("path", SOURCES, ids=lambda path: str(path.relative_to(ROOT)))
def test_file_is_readable(path):
    lines = path.read_text().splitlines()
    too_long = [f"line {number}: {len(line)} characters"
                for number, line in enumerate(lines, start=1) if len(line) > MAX_LINE]
    assert not too_long, f"lines over {MAX_LINE} characters: {too_long[:5]}"
    assert len(lines) <= MAX_FILE_LINES, f"{len(lines)} lines; split it by responsibility"
