#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "beautifulsoup4~=4.14.3",
#   "mdutils~=1.8.1",
#   "pasteboard~=0.4.0; sys_platform == 'darwin'",
#   "jinja2~=3.1.0",
# ]
# ///
"""
Meeting Note Wrapper Script

This script:
1. Copies from the pasteboard and validates HTML content
2. Initializes PromptOrLog with optional --override-mode
3. Prompts for a date (YYYY-MM-DD format), retries or cancels
4. Prompts for a title, allows cancel
5. Extracts meeting participants from the parsed events
6. Asks for confirmation before writing (unless --force is enabled)
7. Writes to Obsidian using the CLI and Jinja2 template
"""
import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from jinja2 import Environment, FileSystemLoader

from scripts.convert_slack_meeting_notes import (
    load_html_from_pasteboard,
    parse_html_from_slack,
    render_markdown_from_events,
    SlackEvent,
)
from scripts.prompt_or_log import Mode, PromptOrLog

logger = logging.getLogger(__name__)

FILE_TITLE = "Meeting Notes - {year}-{month}-{day} - {title}"
DEFAULT_TAGS = ["meeting-notes"]
DEFAULT_OBSIDIAN_FOLDER = "08 - Meeting Notes"


def validate_date_format(date_str: str) -> bool:
    """Validate that date_str matches YYYY-MM-DD format."""
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def extract_participants(events: List[SlackEvent]) -> List[str]:
    """Extract unique participant usernames from the parsed Slack events."""
    participants = set()
    for event in events:
        if event.username:
            participants.add(event.username)
    return sorted(list(participants))


def render_meeting_note(
    date_str: str,
    title: str,
    participants: List[str],
    transcription: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Render the meeting note using the Jinja2 template."""
    if tags is None:
        tags = DEFAULT_TAGS

    # Find the templates directory relative to this script
    script_dir = Path(__file__).parent.parent
    templates_dir = script_dir / "templates"

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("meeting_notes_template_v1.md.jinja")

    meeting_data = {
        "date": date_str,
        "title": title,
        "tags": tags,
        "participants": participants,
        "transcription": transcription,
    }

    return template.render(meeting=meeting_data)


def write_to_obsidian(
    filename: str, content: str, folder: str = DEFAULT_OBSIDIAN_FOLDER
) -> bool:
    """Write the note to Obsidian using the Obsidian CLI.

    Returns True if successful, False otherwise.
    """
    try:
        # Construct the full path for the note
        note_path = f"{folder}/{filename}.md"

        # Use obsidian CLI to create the note with content parameter
        result = subprocess.run(
            ["obsidian", "create", f"path=\"{note_path}\"", f"name=\"{filename}\"" f"content={content}", "overwrite"],
            text=True,
            capture_output=True,
            check=True,
        )
        if result.stderr:
            logger.error(f"Obsidian CLI stderr: {result.stderr}")

        logger.info(f"Successfully created note: {note_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create note in Obsidian: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("obsidian CLI command not found. Please ensure it's installed and in PATH.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create meeting notes from Slack pasteboard content"
    )
    parser.add_argument(
        "--override-mode",
        type=str,
        choices=["auto_detect", "log", "gui"],
        default=None,
        help="Override the mode for PromptOrLog (auto_detect, log, or gui)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt before writing",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity level",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=DEFAULT_OBSIDIAN_FOLDER,
        help=f"Obsidian folder to write to (default: {DEFAULT_OBSIDIAN_FOLDER})",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose == 0 else logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    # Step 1: Load and validate HTML from pasteboard
    logger.info("Loading HTML from pasteboard...")
    try:
        html_source = load_html_from_pasteboard()
    except Exception as e:
        logger.error(f"Failed to load HTML from pasteboard: {e}")
        sys.exit(1)

    if not html_source or not html_source.strip():
        logger.error("Pasteboard content is empty or invalid")
        sys.exit(1)

    logger.info("Parsing Slack HTML content...")
    try:
        events = parse_html_from_slack(html_source)
    except Exception as e:
        logger.error(f"Failed to parse Slack HTML: {e}")
        sys.exit(1)

    if not events:
        logger.error("No events found in the parsed HTML")
        sys.exit(1)

    logger.info(f"Successfully parsed {len(events)} events")

    # Step 2: Initialize PromptOrLog
    override_mode = None
    if args.override_mode:
        mode_map = {
            "auto_detect": Mode.AUTO_DETECT,
            "log": Mode.LOG,
            "gui": Mode.GUI,
        }
        override_mode = mode_map[args.override_mode]

    prompter = PromptOrLog(override_mode)
    logger.debug(f"PromptOrLog initialized with mode: {prompter.get_mode()}")

    # Step 3: Prompt for date with validation and retry
    date_str = None
    while True:
        date_input = prompter.prompt(
            "Enter meeting date (YYYY-MM-DD format):",
            default=datetime.now().strftime("%Y-%m-%d"),
        )

        if date_input is None or date_input.lower() == "cancel":
            logger.info("User cancelled date input")
            sys.exit(0)

        if validate_date_format(date_input):
            date_str = date_input
            logger.info(f"Date set to: {date_str}")
            break
        else:
            logger.warning(f"Invalid date format: {date_input}. Please use YYYY-MM-DD format.")
            # In LOG mode, we can't retry effectively, so exit
            if prompter.get_mode() == Mode.LOG:
                logger.error("Date validation failed in LOG mode. Exiting.")
                sys.exit(1)

    # Step 4: Prompt for title
    title = prompter.prompt("Enter meeting title:", default="Team Meeting")

    if title is None or title.lower() == "cancel":
        logger.info("User cancelled title input")
        sys.exit(0)

    if not title.strip():
        logger.warning("Empty title provided, using default")
        title = "Team Meeting"

    logger.info(f"Title set to: {title}")

    # Step 5: Extract meeting participants
    participants = extract_participants(events)
    logger.info(f"Extracted {len(participants)} participants: {', '.join(participants)}")

    # Render the transcription markdown from events
    transcription = render_markdown_from_events(events)

    # Render the full meeting note
    note_content = render_meeting_note(
        date_str=date_str,
        title=title,
        participants=participants,
        transcription=transcription,
        tags=DEFAULT_TAGS,
    )

    # Parse date for filename
    date_parts = date_str.split("-")
    filename = FILE_TITLE.format(
        year=date_parts[0],
        month=date_parts[1],
        day=date_parts[2],
        title=title,
    )

    # Step 6: Ask for confirmation (unless --force)
    if not args.force:
        confirmation = prompter.dialog(
            f"Create meeting note '{filename}' in folder '{args.folder}'?",
            default=True,
        )
        if not confirmation:
            logger.info("User cancelled the operation")
            sys.exit(0)

    # Step 7: Write to Obsidian
    logger.info(f"Writing note to Obsidian: {filename}")
    success = write_to_obsidian(filename, note_content, folder=args.folder)

    if success:
        logger.info("Meeting note created successfully!")
        sys.exit(0)
    else:
        logger.error("Failed to create meeting note")
        sys.exit(1)


if __name__ == "__main__":
    main()
