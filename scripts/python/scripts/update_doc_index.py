#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-frontmatter~=1.3.0",
#   "gitignore-parser~=0.1.13"
# ]
# ///
import logging
from typing import List
import argparse
import os
from pathlib import Path
from typing import Callable
from dataclasses import dataclass

import gitignore_parser
logger = logging.getLogger(__name__)

@dataclass
class Header:
    

def __run_script():
    pass


def __find_index_builder_ignore(*paths: Path) -> Callable[[str], bool]:
    callables: List[Callable[[str], bool]] = []
    for path in paths:
        if path.exists() & path.is_file():
            try:
                ignore_fn = gitignore_parser.parse_gitignore(path)
                callables.append(ignore_fn)
            except Exception as e:
                logger.warning(f"Ignoring {path}: {e}")
    if len(callables) == 0:
        return lambda path: False
    return lambda path: any(map(lambda fn: not fn, paths))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parse all markdown documents for headers")
    parser.add_argument("root", type=Path, help="Root directory of markdown documents", default=Path.cwd())
    parser.add_argument("paths", nargs="*", help="Paths to markdown files")
    # cwd: Path = Path(os.getcwd())

    args = parser.parse_args()
    # TODO: add gitignore

    __run_script()