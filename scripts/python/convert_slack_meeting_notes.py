#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "beautifulsoup4~=4.14.3",
#   "mdutils~=1.8.1",
#   "pasteboard~=0.4.0; sys_platform == 'darwin'",
# ]
# ///
import argparse
import logging
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup
from mdutils.tools.Table import Table

logger = logging.getLogger(__name__)
PASTEBOARD_AVAILABLE = False
try:
    import pasteboard
    PASTEBOARD_AVAILABLE = True
except ImportError:
    pass

VERBOSE = False
VERY_VERBOSE = False
version = "0.0.1"

HEADER = f"<!-- START {__file__} v{version} -->"
FOOTER = f"<!-- END {__file__} v{version} -->"


@dataclass
class SlackEvent:
    avatar_url: str
    username: str
    event_type: str
    event_text: str

def __load_html_from_pasteboard() -> str:
    if not PASTEBOARD_AVAILABLE:
        raise RuntimeError("pasteboard module is not available.")
    pb = pasteboard.Pasteboard()
    html_content = pb.get_contents(type=pasteboard.HTML)
    if html_content is None:
        logger.info("No HTML content found in the pasteboard. Falling back to html")
        raise RuntimeError("No HTML content in pasteboard")
    return html_content

def __parse_html_from_slack(html_source: str) -> List[SlackEvent]:
    soup = BeautifulSoup(html_source, "html.parser")
    items = soup.select("div[data-qa='virtual-list-item']")
    events: List[SlackEvent] = []

    for item in items:
        # 1) first image inside the block
        img = item.find("img", src=True)
        avatar_url = img["src"].strip() if img else ""

        # 2) text inside p-huddle_event_log__member_name
        name_el = item.select_one(".p-huddle_event_log__member_name")
        username = name_el.get_text(strip=True) if name_el else ""

        # 3) classname of the first span inside p-huddle_event_log__event_text
        # 4) text value inside p-huddle_event_log__event_text
        text_container = item.select_one(".p-huddle_event_log__event_text")
        event_type = ""
        event_text = ""
        if text_container:
            first_span = text_container.find("span")
            if first_span:
                cls = first_span.get("class")
                if isinstance(cls, list):
                    event_type = " ".join(cls).strip()
                elif isinstance(cls, str):
                    event_type = cls.strip()
                event_text = first_span.get_text(strip=True)
            else:
                event_text = text_container.get_text(strip=True)

        events.append(
            SlackEvent(
                avatar_url=avatar_url,
                username=username,
                event_type=event_type,
                event_text=event_text,
            )
        )
    return events

def __create_chat_tuple(event: SlackEvent) -> tuple[str, str, str]:
    italics = ""
    if event.event_type != "p-huddle_event_log__transcription":
        italics = "_"
    return event.avatar_url, event.username, italics + event.event_text + italics

def __run_script(verbose: bool = False, paste: bool = False) -> None:
    html_source = __load_html_from_pasteboard()
    events = __parse_html_from_slack(html_source)
    rows = [__create_chat_tuple(ev) for ev in events if ev.event_text.strip()]
    #         >>> from mdutils.tools.Table import Table
    #         >>> text_list = ['List of Items', 'Description', 'Result', 'Item 1', 'Description of item 1', '10', 'Item 2', 'Description of item 2', '0']
    #         >>> table = Table().create_table(columns=3, rows=3, text=text_list, text_align='center')
    #         >>> print(repr(table))
    # md = mdutils.MdUtils(file_name="slack_meeting_notes")
    # md.new_line(HEADER)
    cells = ["avatar", "user", "text"]
    for avatar, user, text in rows:
        avatar_cell = f"![]({avatar})" if avatar else ""
        cells.extend([avatar_cell, user, text])
    table = Table().create_table(columns=3, rows=len(rows) + 1, text=cells, text_align="left")
    output = f"{HEADER}\n{table}{FOOTER}\n"
    if paste and PASTEBOARD_AVAILABLE:
        pb = pasteboard.Pasteboard()
        pb.set_contents(output, type=pasteboard.String)
        logger.info("Output pasted to clipboard.")
    else:
        print(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert Slack Meeting Notes to Markdown format")
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="The file to parse (markdown document)."
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity level'
    )
    parser.add_argument(
        '--paste', '-p',
        action='store_true',
        help='Paste the output back to the clipboard'
    )

    args = parser.parse_args()

    if args.verbose >= 1:
        VERBOSE = True
    if args.verbose >= 2:
        VERY_VERBOSE = True
    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 3 else logging.INFO,
        format="%(message)s",
    )
    __run_script(verbose=args.verbose, paste=args.paste)
