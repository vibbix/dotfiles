#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-frontmatter~=1.3.0",
#   "gitignore-parser~=0.1.13",
#   "mdutils~=1.8.1",
# ]
# ///
"""Regenerate the ``00-index.md`` table for a folder of numbered markdown docs.

Each doc carries frontmatter (``title``, ``summary``, ``read_if``, ``created``)
that becomes a row in the index. Files matched by an ``.indexbuilderignore``
(gitignore syntax) are skipped, as is the index itself.
"""
import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote

import frontmatter
import gitignore_parser
from mdutils.tools.Table import Table

logger = logging.getLogger(__name__)

INDEX_NAME = "00-index.md"
IGNORE_NAME = ".indexbuilderignore"
MARKER_START = "<!-- doc-index:start -->"
MARKER_END = "<!-- doc-index:end -->"
COLUMNS = ("Doc", "What is it", "Read it if...")


@dataclass
class DocEntry:
    path: Path
    title: str
    summary: str
    read_if: str
    created: datetime | date | None

    @property
    def sort_key(self) -> tuple[int, object]:
        """Entries with a ``created`` date sort first (ascending), rest by name."""
        if self.created is None:
            return (1, self.path.name)
        when = self.created
        if isinstance(when, datetime):
            when = when.date()
        return (0, when.isoformat())


def build_ignore_matcher(*ignore_files: Path) -> Callable[[Path], bool]:
    matchers: list[Callable[[str], bool]] = []
    for path in ignore_files:
        if not path.is_file():
            continue
        try:
            matchers.append(gitignore_parser.parse_gitignore(path))
        except Exception as exc:
            logger.warning("Skipping ignore file %s: %s", path, exc)
    if not matchers:
        return lambda _path: False
    return lambda candidate: any(match(str(candidate)) for match in matchers)


def discover_ignore_files(root: Path) -> list[Path]:
    candidate = (root / IGNORE_NAME).resolve()
    return [candidate] if candidate.is_file() else []


def load_entry(path: Path) -> DocEntry:
    post = frontmatter.load(path)
    title = str(post.get("title") or path.name)
    return DocEntry(
        path=path.resolve(),
        title=title,
        summary=str(post.get("summary") or ""),
        read_if=str(post.get("read_if") or ""),
        created=post.get("created"),
    )


def collect_entries(
    root: Path, index_path: Path, is_ignored: Callable[[Path], bool]
) -> list[DocEntry]:
    entries: list[DocEntry] = []
    for path in sorted(root.rglob("*.md")):
        resolved = path.resolve()
        if resolved == index_path:
            continue
        if is_ignored(resolved):
            logger.debug("Ignored %s", path)
            continue
        try:
            entries.append(load_entry(path))
        except Exception as exc:
            logger.warning("Could not parse %s: %s", path, exc)
    return sorted(entries, key=lambda e: e.sort_key)


def _cell(text: str) -> str:
    """Collapse newlines; mdutils' Table escapes pipe characters itself."""
    return text.replace("\n", " ").strip()


def _doc_link(entry: DocEntry, index_dir: Path) -> str:
    """Display text comes from ``title`` (the project-relative path by convention);
    the link is resolved relative to the index file's location."""
    href = quote(Path(os.path.relpath(entry.path, index_dir)).as_posix())
    return f"[{_cell(entry.title)}]({href})"


def render_table(entries: list[DocEntry], index_dir: Path) -> str:
    cells = list(COLUMNS)
    for e in entries:
        cells.extend([_doc_link(e, index_dir), _cell(e.summary), _cell(e.read_if)])
    table = Table().create_table(
        columns=len(COLUMNS),
        rows=len(entries) + 1,
        text=cells,
        text_align="left",
    )
    return table.strip()


def splice_index(existing: str, table: str) -> str:
    block = f"{MARKER_START}\n{table}\n{MARKER_END}"
    if MARKER_START in existing and MARKER_END in existing:
        head, _, rest = existing.partition(MARKER_START)
        _, _, tail = rest.partition(MARKER_END)
        return f"{head}{block}{tail}"
    base = existing.rstrip()
    if not base:
        base = "# Index"
    return f"{base}\n\n{block}\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate the markdown doc index table from frontmatter."
    )
    parser.add_argument(
        "root", type=Path, nargs="?", default=Path.cwd(),
        help="Directory of markdown documents to scan (default: cwd)",
    )
    parser.add_argument(
        "--index", type=Path, default=None,
        help=f"Index file to write (default: <root>/{INDEX_NAME})",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Exit non-zero if the index is out of date; write nothing.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    root: Path = args.root.resolve()
    if not root.is_dir():
        logger.error("Root is not a directory: %s", root)
        return 2

    index_path = (args.index or root / INDEX_NAME).resolve()

    is_ignored = build_ignore_matcher(*discover_ignore_files(root))
    entries = collect_entries(root, index_path, is_ignored)
    logger.info("Indexed %d document(s) under %s", len(entries), root)

    table = render_table(entries, index_path.parent)
    existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    updated = splice_index(existing, table)

    if args.check:
        if updated != existing:
            logger.error("Index is out of date: %s", index_path)
            return 1
        logger.info("Index is up to date.")
        return 0

    if updated != existing:
        index_path.write_text(updated, encoding="utf-8")
        logger.info("Wrote %s", index_path)
    else:
        logger.info("Index already up to date: %s", index_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
