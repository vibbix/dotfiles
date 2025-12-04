#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pexpect<=4.9.0",
# ]
# ///
import asyncio
import re
import struct, fcntl, termios, signal, sys
from re import Pattern
from typing import AnyStr

import pexpect
from pexpect import spawn


def handle_passthrough(process: spawn):
    def sigwinch_passthrough (sig, data):
        s = struct.pack("HHHH", 0, 0, 0, 0)
        a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(),
            termios.TIOCGWINSZ , s))
        if not process.closed:
            process.setwinsize(a[0],a[1])
    signal.signal(signal.SIGWINCH, sigwinch_passthrough)

# def handle_input(bytes: AnyStr) -> AnyStr:
#     # Handle input here
#     # For example, you can decode bytes to string
#     decoded_input = bytes.decode("utf-8")
#     return bytes

async def __main__():
    print("loading")
    QUERY="""((assignee = currentUser()) OR (creator = currentUser() && assignee = EMPTY)) AND (statusCategory != Done)""" #formerly = In Progress
    #QUERY = "assignee = currentUser()"
    #child = pexpect.spawn("jira", )
    #SELECTED_ISSUE=$(JIRA_FORCE_INTERACTIVE=1 jira issue list -q "$QUERY" --order-by created --json --select-on-enter)\
    args = ["issue", "list", "-q", QUERY, "--order-by", "created", "--json", "--select-on-enter"]
    #set dimensions
    #output = TextIO()
    child = pexpect.spawn("jira", args = args)
    handle_passthrough(child)
    #child.logfile = output
    #idx = child.expect(r"\033\[2J", async_=True)

    # child.interact(escape_character='\r', input_filter=handle_input)
    child.interact(escape_character='\r')#, input_filter=handle_input)
    child.waitnoecho()
    child.sendline("\r")
    idx = child.expect(rb"\x1b[?1004l")
    output = child.after.decode("utf-8")  # Decode if the output is in bytes
    print(f"Captured Output: {output}")
    #print(output)
    # read = output.readline()
    # #output = child.before.decode("utf-8")  # Decode if the output is in bytes
    # print(f"Captured Output: {read}")
    # print(child.stdout)
asyncio.run(__main__())