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

def extract_includes(c_file):
    includes = []
    with open(c_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r'#include\s+"([^"]+)"', line)
            if m:
                includes.append(m.group(1))
    return includes

def main(directory):
    edges = set()
    c_files = find_c_files(directory)
    for c_file in c_files:
        base = os.path.relpath(c_file, directory)
        includes = extract_includes(c_file)
        for inc in includes:
            # Show relation: c_file --> inc
            edges.add((base, inc))
    print("```mermaid")
    print("graph TD")
    for src, dst in sorted(edges):
        print(f'  "{src}" --> "{dst}";')
    print("```")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mermaid includes diagram for .c files")
    parser.add_argument("directory", help="Directory to scan recursively", default=os.getcwd())
    args = parser.parse_args()
    main(args.directory)