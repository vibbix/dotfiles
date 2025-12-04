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
from sys import stderr
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

def trace_to_main(edges : Set[tuple[str,str]], main_node: str) -> Set[str]:
    """Recursively find all edges that connect to main_node."""
    traced:  Set[tuple[str,str]]= set()
    marked_nodes: Set[str] = set()
    reverse_map = {}
    for src, dst in edges:
        reverse_map.setdefault(src, set()).add(dst)
#    print(f"reverse map: {reverse_map}", file=stderr)
    node_stack : list[str] = [main_node]
    while node_stack:
        node = node_stack.pop()
#        print(f"Popped node: {node}", file=stderr)
#        print(f"node set: {reverse_map.get(node, [])}", file=stderr)
        for src in reverse_map.get(node, []):
            edge = (src, node)
            if edge not in traced:
                marked_nodes.add(src)
                marked_nodes.add(node)
                traced.add(edge)
                node_stack.append(src)
    return marked_nodes

def main(directory: str, color_main_name: str ="main"):
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
            edges.add((base, inc))
            inc_folder = os.path.dirname(inc)
            nodes_by_folder.setdefault(inc_folder, set()).add(clean_path(inc))
    print("graph TD")
    for folder, nodes in sorted(nodes_by_folder.items()):
        if folder and folder != ".":
            print(f"\tsubgraph {folder}")
            for node in sorted(nodes):
                print(f'\t\t{clean_path(node)}')
            print("\tend")
    # Print edges and collect for coloring
    clean_edges: Set[tuple[str,str]] = set()
    for src, dst in sorted(edges):
        clean_src = clean_path(src)
        clean_dst = clean_path(dst)
        if (clean_src != clean_dst):
            print(f'\t{clean_src} --> {clean_dst};')
            clean_edges.add((clean_src, clean_dst))
    # init style
    print("\t%% Highlight path to main")
    print("\tclassDef MainTrace fill:#ff0,stroke:#333,stroke-width:2px;")
    # Print node labels
    name_set = set()
    for src, dst in edges:
        if (src not in name_set):
            print(f'\t{clean_path(src)}["{src}"]')
            name_set.add(src)
        if (dst not in name_set):
            print(f'\t{clean_path(dst)}["{dst}"]')
            name_set.add(dst)
#    main_clean = clean_path(color_main_name)1
    main_edges = trace_to_main(clean_edges, color_main_name)
    if main_edges:
        for node in main_edges:
            print(f'\tclass {node} MainTrace;')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mermaid includes diagram for .[c|h] files")
    parser.add_argument("directory", help="Directory to scan recursively", default=os.getcwd())
    parser.add_argument("--color_main", help="Node name to trace and color path to (default: main)", default="main")
    args = parser.parse_args()
    main(args.directory, args.color_main)