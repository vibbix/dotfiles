# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pywinauto",
# ]
# [tool.uv]
# exclude-newer = "2025-07-06T00:00:00Z"
# ///
from pywinauto.application import Application
#app = Application(backend="uia").start("C:\Program Files\HWiNFO64\HWiNFO64.EXE")

app = Application(backend="uia").connect(pid=94356)
