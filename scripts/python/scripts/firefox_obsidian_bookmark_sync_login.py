#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyfxa~=0.8.1",
#   "pyotp~=2.9.0",
# ]
# ///

import os
from pyotp import parse_uri, TOTP

from fxa.core import Client as FxAClient
# from syncclient.client import SyncClient, TOKENSERVER_URL

FXA_SERVER_URL = "https://api.accounts.firefox.com"

def main():
    email = os.environ["FXA_EMAIL"]
    password = os.environ["FXA_PASSWORD"]
    totp = os.environ.get("FXA_TOTP", "")
    client = FxAClient(server_url=FXA_SERVER_URL)
    print(email)
    session = client.login(email, password, keys=True)
    print("logged in")
    print(f"{session.get_email_status()} - {session.verificationMethod}")
    if session.verificationMethod == "totp-2fa":
        if totp:
            print(totp)
            session.totp_verify(process_totp(totp))
        else:
            print("Verification method not supported")
            exit(1)
    print(f"{session.get_email_status()} - {session.verificationMethod}")

    keys = session.fetch_keys()
    print(keys)

def process_totp(totp: str) -> str:
    if len(totp) == 6:
        return totp
    if totp.startswith("otpauth://"):
        otp = parse_uri(totp)  # validate the URI
        if isinstance(otp, TOTP):
            return otp.now()
    raise ValueError("Invalid TOTP")

if __name__ == "__main__":
    main()
