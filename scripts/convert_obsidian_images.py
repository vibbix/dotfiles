#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyvips>=3.0.0",
#     "tqdm>=4.67.1",
# ]
# ///

from datetime import datetime
import sys
import os
from pathlib import Path
import re
from re import Match
from typing import Final
import pyvips
from dataclasses import dataclass


@dataclass
class ConvertedImage:
    original_path: Path
    new_path: Path
    original_size: int
    new_size: int
    date_created: datetime
    date_modified: datetime


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: convert_obsidian_images.py <vault_folder>")
        sys.exit(1)

    vault_path = Path(sys.argv[1])
    #.resolve()
    obsidian_folder = vault_path / ".obsidian"
    if not obsidian_folder.exists() or not obsidian_folder.is_dir():
        print(f"Error: {vault_path} is not an Obsidian vault (missing .obsidian folder)")
        sys.exit(1)

    # Find all .png images recursively
    png_files = list(vault_path.rglob("*.png"))
    if not png_files:
        print("No PNG images found.")
        return

    # Find all markdown files
    md_files = list(vault_path.rglob("*.md"))


    # TODO: Optimization strategy
    # Check for files whose Date-Modified is older than Date-Created of the PNG
    for png_file in png_files:
        print(f"Image: {png_file}")
        png_name = png_file.name
        found_in = []
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                # TODO: add logging
                continue
            # Markdown image/link: ![alt](path/to/image.png) or [alt](path/to/image.png)
            possible_found_in : re.Match[str] | None = re.search(rf'[\[\(][^\]\)]*({re.escape(png_name)})[\]\)]', content)
            if possible_found_in:
                print(f"  Found in {md_file} -> \"{possible_found_in.group(0)}\" aka \"{possible_found_in.group(1)}\"")
                found_in.append(md_file)
        if len(found_in) > 0:
            print("  Referenced in:")
            for md in found_in:
                print(f"    {md}")
            # ask to confirm replacement
            response = input(f"  Replace references to '{png_name}' with webp version? (y/n) ")
            if response.lower() != 'y':
                print("  Skipping conversion.")
                continue
            converted_image = create_converted_image(png_file)
            if converted_image:
                append_to_log([converted_image], vault_path / "00 - Meta/Logs/Converted Files.md")
                for md in found_in:
                    try:
                        md_content = md.read_text(encoding="utf-8")
                        updated_content = replace_image_references(md_content, png_name, converted_image.new_path.name)
                        md.write_text(updated_content, encoding="utf-8")
                        print(f"  Updated references in {md}")
                    except Exception as e:
                        print(f"  Failed to update {md}: {e}")
                # delete original png
                try:
                    os.remove(png_file)
                    print(f"  Deleted original PNG: {png_file}")
                except Exception as e:
                    print(f"  Failed to delete original PNG {png_file}: {e}")
        else:
            print("  Not referenced in any markdown file.")


def replace_image_references(md_content: str, original_name: str, new_name: str) -> str:
    # Replace all occurrences of original_name with new_name in markdown image/link syntax
    updated_content = re.sub(rf'(!?\[.*?\]\(.*?){re.escape(original_name)}(.*?\))', rf'\1{new_name}\2', md_content)
    return updated_content

def create_converted_image(img_path: Path) -> ConvertedImage | None:
    #print("| Filename | Original Size | New Filename | New Size | Date Created | Date Modified |")
    #print("| -------- | ------------- | ------------ | -------- | ------------ | ------------- |")
    # date_created : Final[float] = img_path.stat().st_ctime
    # png_image = pyvips.Image.new_from_file(str(img_path), access="sequential")
        # 1. Get date_created as Final[datetime]
    stat = img_path.stat()
    date_created: Final[datetime.datetime] = datetime.fromtimestamp(stat.st_birthtime)

    # 2. Load the image to vips
    try:
        png_image = pyvips.Image.new_from_file(str(img_path), access="sequential")
    except Exception as e:
        print(f"Failed to load image {img_path}: {e}")
        return None

    # 3. Save the image as a lossless webp using pyvips, change extension to .webp
    new_path = img_path.with_suffix('.webp')
    try:
        png_image.write_to_file(str(new_path), Q=100, lossless=True, strip=False)
    except Exception as e:
        print(f"Failed to save webp for {img_path}: {e}")
        return None

    # 4. Return the filled out ConvertedImage dataclass
    original_size = stat.st_size
    new_stat = new_path.stat() if new_path.exists() else None
    new_size = new_stat.st_size if new_stat else 0
    date_modified: Final[datetime] = datetime.fromtimestamp(new_stat.st_mtime)

    return ConvertedImage(
        original_path=img_path,
        new_path=new_path,
        original_size=original_size,
        new_size=new_size,
        date_created=date_created,
        date_modified=date_modified,
    )

def append_to_log(converted_images: list[ConvertedImage], log_path: Path, relative_path: Path = Path("/")) -> None:
    with log_path.open("a", encoding="utf-8") as log_file:
        for img in converted_images:
            # todo - fix relative path
            # | Filename | Original Size | New Filename | New Size | Date Created | Date Modified |
            log_file.write(f"|{img.original_path.relative_to(relative_path)} | {img.original_size / 1000} KB | {img.new_path.relative_to(relative_path)} | {img.new_size / 1000} KB | {img.date_created.isoformat()} | {img.date_modified.isoformat()} |\n")


if __name__ == "__main__":
    main()