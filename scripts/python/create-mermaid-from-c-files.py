#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pexpect<=4.9.0",
# ]
# ///
import os
import re
import argparse
from typing import Set

def find_src_files(directory: os.PathLike):
    src_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.c') or file.endswith('.h'):
                src_files.append(os.path.join(root, file))
    return src_files

def extract_includes(src_file: os.PathLike, directory: os.PathLike) -> tuple[list[str], bool]:
    includes = []
    c_dir = os.path.dirname(os.path.relpath(src_file, directory))
    with open(src_file, encoding="utf-8", errors="ignore") as f:
        has_main: bool = False
        for line in f:
            m = re.match(r'#include\s+"([^"]+)"', line)
            if m:
                # Attach the directory prefix to local includes
                inc_path = os.path.normpath(os.path.join(c_dir, m.group(1)))
                # Strip the file extension for the graph
                inc_path = inc_path.replace('.c', '').replace('.h', '')
                includes.append(inc_path)
            if src_file.endswith('.c'):
                #TODO better check if this is a comment
                if line.count('int main') > 0:
                    has_main = True
    return includes, has_main

def clean_path(import_path: str) -> str:
    """Clean the path to be relative and normalized."""
    ipath = import_path.replace('.c', '').replace('.h', '').replace(' ', '_').replace('.', '_')
    if ipath == "graph":
        ipath = "graph_"
    return ipath

def main(directory):
    edges: Set[tuple[str,str]] = set()
    nodes_by_folder = {}
    src_files = find_src_files(directory)
    for src_file in src_files:
        base = os.path.normpath(os.path.relpath(src_file, directory))
        folder = os.path.dirname(base)
        nodes_by_folder.setdefault(folder, set()).add(clean_path(base))
        includes, has_main = extract_includes(src_file, directory)
        if has_main:
            nodes_by_folder.setdefault("cli", set()).add(clean_path(base))
        for inc in includes:
            # Show relation: src_file --> inc, both with dir prefix
            edges.add((base, inc))
            inc_folder = os.path.dirname(inc)
            nodes_by_folder.setdefault(inc_folder, set()).add(clean_path(inc))
    print("graph TD")
    # Print subgraphs for each folder
    for folder, nodes in sorted(nodes_by_folder.items()):
        if folder and folder != ".":
            print(f"\tsubgraph {folder}")
            for node in sorted(nodes):
                print(f'\t\t{clean_path(node)}')
            print("\tend")
    # Print edges
    for src, dst in sorted(edges):
        clean_src = clean_path(src)
        clean_dst = clean_path(dst)
        if (clean_src != clean_dst):
            # Avoid self-loops
            print(f'\t{clean_src} --> {clean_dst};')


    name_set = set()
    for src, dst in edges:
        if (src not in name_set):
            print(f'\t{clean_path(src)}["{src}"]')
            name_set.add(src)
        if (dst not in name_set):
            print(f'\t{clean_path(dst)}["{dst}"]')
            name_set.add(dst)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mermaid includes diagram for .[c|h] files")
    parser.add_argument("directory", help="Directory to scan recursively", default=os.getcwd())
    args = parser.parse_args()
    main(args.directory)