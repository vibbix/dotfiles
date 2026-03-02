#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "beautifulsoup4~=4.14.3",
#   "PyChromeDevTools~=1.0.4"
# ]
# ///

import argparse

from PyChromeDevTools import ChromeInterface
from scripts.convert_slack_meeting_notes import render_markdown_from_events, parse_html_from_slack, SlackEvent

js = """
{
    async function printHuddleHtml() {
        const allWindows = BrowserWindow.getAllWindows();
        const targetWindow = allWindows.find(w =>
            (w.accessibleTitle || "").startsWith('Huddle')
        );

        if (!targetWindow) {
            throw new Error("No window found starting with 'Huddle'");
        }

        const html = await targetWindow.webContents.executeJavaScript('document.documentElement.outerHTML');
        return html;
    }

    printHuddleHtml()
}
"""

def __execute_js(chrome, js):
    params = {"expression": js, "returnByValue": True, "awaitPromise": True}
    result = chrome.Runtime.evaluate(**params)
    return result

def get_html(cdp) -> str:
    # attempt to load BrowserWindow
    __execute_js(cdp, "const { BrowserWindow } = require('electron');")
    transcript_html_res = __execute_js(cdp, js)
    n_res_parent = transcript_html_res[0]['result']
    if 'exceptionDetails' in n_res_parent.keys():
        raise ValueError(f"JavaScript execution error: {n_res_parent['exceptionDetails']}")
    result = n_res_parent['result']
    if {'type', 'value'} != set(result.keys()):
        raise ValueError(f"Unexpected result structure:[{result.keys()}]")
    if result['type'] != 'string':
        raise ValueError(f"Unexpected result type: {result['type']}")
    return result['value']

def __run_script():
    # TODO: check if port 9229 is running a slack instance
    try:
        slack_cdp = ChromeInterface(port=9229)
        html = get_html(slack_cdp)
        events = parse_html_from_slack(html)
        markdown = render_markdown_from_events(events)
        print(markdown)
    except Exception as e:
        print(f"Error connecting to Slack CDP: {e}")
        return

def __install():
    """
    Installs the script
    """

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Connect to a running slack instance and scrape huddle data.")
    args = parser.parse_args()
    # TODO: "add --install" option to launch slack with --remote-debugging-port=9229
    # TODO: "add --live" option to keep connection open and stream data
    # TODO: "add --output <file>" option to save output to file
    # TODO: "add --template <file>" option to use custom markdown template
    __run_script()