from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import sys

import yaml
from rich.console import Console
from rich.tree import Tree

log = logging.getLogger(__name__)

DEFAULT_OBSIDIAN_FOLDER = "02 - Remote Data Sources/Firefox Bookmarks"
OBSIDIAN_SYNC_PROPERTY  = "sync_id:firefox"


class BookmarkType(StrEnum):
    BOOKMARK     = "bookmark"
    MICROSUMMARY = "microsummary"
    QUERY        = "query"
    FOLDER       = "folder"
    LIVEMARK     = "livemark"
    SEPARATOR    = "separator"


@dataclass
class BookmarkBase:
    id:          str
    parentid:    str
    parent_name: str
    type:        BookmarkType
    date_added:  int | None = None  # milliseconds since epoch; nullable (*int64 in Go)
    deleted:     bool = False
    has_dupe:    bool = False


@dataclass
class _LinkBase(BookmarkBase):
    """Shared fields for bookmark / microsummary / query."""
    title:           str       = ""
    uri:             str       = ""
    description:     str       = ""
    load_in_sidebar: bool      = False
    tags:            list[str] = field(default_factory=list)
    keyword:         str       = ""


@dataclass
class Bookmark(_LinkBase):
    type: BookmarkType = BookmarkType.BOOKMARK


@dataclass
class MicroSummary(_LinkBase):
    type:          BookmarkType = BookmarkType.MICROSUMMARY
    generator_uri: str          = ""
    static_title:  str          = ""


@dataclass
class Query(_LinkBase):
    type:        BookmarkType = BookmarkType.QUERY
    folder_name: str          = ""
    query_id:    str          = ""


@dataclass
class Folder(BookmarkBase):
    type:     BookmarkType = BookmarkType.FOLDER
    title:    str          = ""
    children: list[str]    = field(default_factory=list)


@dataclass
class Livemark(BookmarkBase):
    type:     BookmarkType = BookmarkType.LIVEMARK
    title:    str          = ""
    children: list[str]    = field(default_factory=list)
    feed_uri: str          = ""
    site_uri: str          = ""


@dataclass
class Separator(BookmarkBase):
    type:               BookmarkType = BookmarkType.SEPARATOR
    separator_position: int          = 0


BookmarkPayload = Bookmark | MicroSummary | Query | Folder | Livemark | Separator


@dataclass
class ObsidianBookmark:
    title:     str
    file_path: str
    tags:      list[str]                = field(default_factory=list)
    created:   datetime.datetime | None = None
    date:      datetime.date | None     = None
    source:    str | None               = None


def parse_bookmark(data: dict, parent_id: str = "", parent_name: str = "") -> BookmarkPayload:
    btype = BookmarkType(data["type"])
    base = {
        "id":          data["id"],
        "type":        btype,
        "parentid":    parent_id,
        "parent_name": parent_name,
        "date_added":  data.get("added_unix"),
        "deleted":     data.get("deleted", False),
        "has_dupe":    data.get("hasDupe", False),
    }
    link = {
        "title":           data.get("title", ""),
        "uri":             data.get("uri", ""),
        "description":     data.get("description", ""),
        "load_in_sidebar": data.get("loadInSidebar", False),
        "tags":            data.get("tags") or [],
        "keyword":         data.get("keyword", ""),
    }
    match btype:
        case BookmarkType.BOOKMARK:
            return Bookmark(**base, **link)
        case BookmarkType.MICROSUMMARY:
            return MicroSummary(
                **base, **link,
                generator_uri=data.get("generatorUri", ""),
                static_title=data.get("staticTitle", ""),
            )
        case BookmarkType.QUERY:
            return Query(
                **base, **link,
                folder_name=data.get("folderName", ""),
                query_id=data.get("queryId", ""),
            )
        case BookmarkType.FOLDER:
            return Folder(
                **base,
                title=data.get("title", ""),
                children=[c.get("id", "") for c in data.get("children") or []],
            )
        case BookmarkType.LIVEMARK:
            return Livemark(
                **base,
                title=data.get("title", ""),
                children=[c.get("id", "") for c in data.get("children") or []],
                feed_uri=data.get("feedUri", ""),
                site_uri=data.get("siteUri", ""),
            )
        case BookmarkType.SEPARATOR:
            return Separator(**base, separator_position=data.get("pos", 0))
        case _:
            raise ValueError(f"unknown bookmark type: {btype!r}")


def _walk_bookmarks(
    node: dict,
    parent_id: str = "",
    parent_name: str = "",
) -> list[BookmarkPayload]:
    results = []
    try:
        results.append(parse_bookmark(node, parent_id=parent_id, parent_name=parent_name))
    except (ValueError, KeyError) as e:
        log.warning("Skipping malformed bookmark %r: %s", node.get("id", "<no id>"), e)

    node_id    = node.get("id", "")
    node_title = node.get("title", "")
    for child in node.get("children") or []:
        results.extend(_walk_bookmarks(child, parent_id=node_id, parent_name=node_title))

    return results


async def _obsidian(*args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "obsidian", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def load_firefox_bookmarks(bookmarks_file: Path) -> list[BookmarkPayload]:
    # TODO: load bookmarks.json directly from the active Firefox profile instead of requiring a file path
    raw: dict = json.loads(bookmarks_file.read_text(encoding="utf-8"))
    log.debug("Loaded %s", bookmarks_file)

    bookmarks: list[BookmarkPayload] = []
    for root_name, root_node in raw["bookmarks"].items():
        bookmarks.extend(_walk_bookmarks(root_node, parent_name=root_name))

    return bookmarks


async def load_obsidian_bookmarks(
    folder: str = DEFAULT_OBSIDIAN_FOLDER,
) -> list[ObsidianBookmark]:
    raw = await _obsidian("search", f"query={OBSIDIAN_SYNC_PROPERTY}", f"path={folder}", "format=json")
    if not raw:
        log.warning("No Obsidian bookmarks found in %r", folder)
        return []

    paths: list[str] = json.loads(raw)
    log.debug("Found %d Obsidian bookmarks in %r", len(paths), folder)

    results: list[ObsidianBookmark] = []
    for path in paths:
        props_yaml = await _obsidian("properties", f"path={path}")
        props: dict = yaml.safe_load(props_yaml) or {}
        results.append(ObsidianBookmark(
            title=Path(path).stem,
            file_path=path,
            tags=props.get("tags") or [],
            created=props.get("created"),
            date=props.get("date"),
            source=props.get("source"),
        ))

    return results


def _build_tree(node: dict, tree: Tree) -> None:
    btype = node.get("type", "")
    title = node.get("title") or node.get("id", "<untitled>")

    if btype == "folder":
        branch = tree.add(f"[bold blue][DIR] {title}[/bold blue]")
        for child in node.get("children") or []:
            _build_tree(child, branch)
    elif btype == "separator":
        tree.add("[dim]---[/dim]")
    else:
        uri = node.get("uri", "")
        label = f"[green]{title}[/green]"
        if uri:
            label += f"  [dim]{uri}[/dim]"
        tree.add(label)


def print_firefox_bookmarks_tree(raw: dict) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    console = Console(legacy_windows=False)
    root = Tree("[bold]Firefox Bookmarks[/bold]")
    for root_node in raw["bookmarks"].values():
        _build_tree(root_node, root)
    console.print(root)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Firefox bookmarks to Obsidian")
    parser.add_argument(
        "bookmarks_file",
        nargs="?",
        type=Path,
        default=Path("bookmarks.json"),
        help="Path to bookmarks.json (default: ./bookmarks.json)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    raw: dict = json.loads(args.bookmarks_file.read_text(encoding="utf-8"))
    print_firefox_bookmarks_tree(raw)

    bookmarks = await load_firefox_bookmarks(args.bookmarks_file)
    obsidian_bookmarks = await load_obsidian_bookmarks()


if __name__ == "__main__":
    asyncio.run(main())