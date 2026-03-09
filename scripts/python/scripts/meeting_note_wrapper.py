from typing import List

from pymsgbox import *

from scripts.convert_slack_meeting_notes import load_html_from_pasteboard, parse_html_from_slack, SlackEvent

FILE_TITLE = "Meeting Notes - {month}-{day}-{year} - {title}"


def __run_script():
    html_source: str = load_html_from_pasteboard()
    events : List[SlackEvent] = parse_html_from_slack(html_source)
    # ask for title

if __name__ == "__main__":
    __run_script()
    #
    # meeting_note = prompt("Please enter the meeting note:")
    # if meeting_note:
    #     print("Meeting Note:")
    #     print(meeting_note)
    # else:
    #     print("No meeting note entered.")