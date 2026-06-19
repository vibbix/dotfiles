#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-frontmatter~=1.3.0",
#   "gitignore-parser~=0.1.13",
#   "mdutils~=1.8.1",
#   "PyYAML~=6.0.3",
# ]
# ///
"""Regenerate the ``00-index.md`` table for a folder of numbered markdown docs.

Each doc carries frontmatter (``title``, ``summary``, ``read_if``, ``created``)
that becomes a row in the index. Files matched by an ``.indexbuilderignore``
(gitignore syntax) are skipped, as is the index itself.

Vendored files that cannot carry frontmatter can be listed in a
``.indexbuilderinclude.{json,yaml,yml}`` at the root, supplying the same column
criteria inline. Included entries override auto-discovered ones at the same path.
"""
import argparse
import json
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
import yaml
from mdutils.tools.Table import Table

logger = logging.getLogger(__name__)

INDEX_NAME = "00-index.md"
IGNORE_NAME = ".indexbuilderignore"
INCLUDE_BASENAME = ".indexbuilderinclude"
INCLUDE_KEYS = ("files", "include", "includes")
MARKER_START = "<!-- doc-index:start -->"
MARKER_END = "<!-- doc-index:end -->"
COLUMNS = ("Doc", "What is it", "Read it if...")


@dataclass
class DocEntry:
    path: Path
    title: str
    summary: str
    read_if: str
    created: date | None

    @property
    def sort_key(self) -> tuple[int, str]:
        """Entries with a ``created`` date sort first (ascending), rest by name."""
        if self.created is None:
            return (1, self.path.name)
        return (0, self.created.isoformat())


def _coerce_date(value: object) -> date | None:
    """Accept a YAML/JSON date, datetime, or ISO string; ``None`` if unparseable."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            logger.warning("Unparseable created date: %r", value)
    return None


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
        created=_coerce_date(post.get("created")),
    )


def discover_include_file(root: Path) -> Path | None:
    for suffix in (".json", ".yaml", ".yml"):
        candidate = root / f"{INCLUDE_BASENAME}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def load_includes(include_file: Path, root: Path) -> list[DocEntry]:
    """Parse the include file into entries. ``path`` is required and resolved
    relative to the include file's directory; other columns mirror the frontmatter."""
    try:
        raw = include_file.read_text(encoding="utf-8")
        data = json.loads(raw) if include_file.suffix == ".json" else yaml.safe_load(raw)
    except Exception as exc:
        logger.warning("Could not read include file %s: %s", include_file, exc)
        return []

    if isinstance(data, dict):
        data = next((data[k] for k in INCLUDE_KEYS if isinstance(data.get(k), list)), [])
    if not isinstance(data, list):
        logger.warning("Include file %s is not a list of entries; ignoring.", include_file)
        return []

    entries: list[DocEntry] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("path"):
            logger.warning("Skipping include entry without a 'path': %r", item)
            continue
        rel = str(item["path"])
        resolved = (root / rel).resolve()
        if not resolved.exists():
            logger.warning("Included file does not exist: %s", resolved)
        entries.append(
            DocEntry(
                path=resolved,
                title=str(item.get("title") or rel),
                summary=str(item.get("summary") or ""),
                read_if=str(item.get("read_if") or ""),
                created=_coerce_date(item.get("created")),
            )
        )
    return entries


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
    return entries


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
    merged: dict[Path, DocEntry] = {
        e.path: e for e in collect_entries(root, index_path, is_ignored)
    }
    include_file = discover_include_file(root)
    if include_file:
        for entry in load_includes(include_file, root):
            merged[entry.path] = entry  # explicit includes override discovery

    entries = sorted(merged.values(), key=lambda e: e.sort_key)
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
