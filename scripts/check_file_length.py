"""Fail when a file exceeds the repository's maximum line count."""

import argparse
import sys
from pathlib import Path

DEFAULT_MAX_LINES = 250
EXCLUDED_PATH_PARTS = ("migrations", "versions")


def count_lines(path: Path) -> int:
    with path.open(encoding="utf-8") as file:
        return sum(1 for _ in file)


def is_excluded(path: Path) -> bool:
    parts = path.parts
    size = len(EXCLUDED_PATH_PARTS)
    return any(parts[start : start + size] == EXCLUDED_PATH_PARTS for start in range(len(parts)))


def find_offenders(paths: list[str], max_lines: int) -> list[str]:
    offenders = []
    for raw_path in paths:
        path = Path(raw_path)
        if is_excluded(path):
            continue
        line_count = count_lines(path)
        if line_count > max_lines:
            offenders.append(f"{raw_path}: {line_count} lines (max {max_lines})")
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    offenders = find_offenders(args.files, args.max_lines)
    for offender in offenders:
        print(offender)
    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main())
