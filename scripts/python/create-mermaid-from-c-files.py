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

def find_c_files(directory: str):
    c_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.c'):
                c_files.append(os.path.join(root, file))
    return c_files

def extract_includes(c_file, directory):
    includes = []
    c_dir = os.path.dirname(os.path.relpath(c_file, directory))
    with open(c_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r'#include\s+"([^"]+)"', line)
            if m:
                # Attach the directory prefix to local includes
                inc_path = os.path.normpath(os.path.join(c_dir, m.group(1)))
                includes.append(inc_path)
    return includes

def clean_path(import_path: str) -> str:
    """Clean the path to be relative and normalized."""
    return import_path.replace(' ', '_').replace('.', '_')
def main(directory):
    edges = set()
    nodes_by_folder = {}
    c_files = find_c_files(directory)
    for c_file in c_files:
        base = os.path.normpath(os.path.relpath(c_file, directory))
        folder = os.path.dirname(base)
        nodes_by_folder.setdefault(folder, set()).add(base)
        includes = extract_includes(c_file, directory)
        for inc in includes:
            # Show relation: c_file --> inc, both with dir prefix
            edges.add((base, inc))
            inc_folder = os.path.dirname(inc)
            nodes_by_folder.setdefault(inc_folder, set()).add(inc)
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
        print(f'\t{clean_path(src)} --> {clean_path(dst)};')

    name_set = set()
    for src, dst in edges:
        if (src not in name_set):
            print(f'\t{clean_path(src)}["{src}"]')
            name_set.add(src)
        if (dst not in name_set):
            print(f'\t{clean_path(dst)}["{dst}"]')
            name_set.add(dst)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mermaid includes diagram for .c files")
    parser.add_argument("directory", help="Directory to scan recursively", default=os.getcwd())
    args = parser.parse_args()
    main(args.directory)