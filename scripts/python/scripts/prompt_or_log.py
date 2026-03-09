from __future__ import annotations

from enum import Enum
from typing import Optional
import os
import sys
import logging

LOG = logging.getLogger(__name__)

class Mode(Enum):
    """Operating mode for PromptOrLog.

    Values:
        AUTO_DETECT: Let the class decide between GUI or log/console.
        LOG: Use console/log based interaction.
        GUI: Use a simple GUI prompt when possible.
    """

    AUTO_DETECT = "auto_detect"
    LOG = "log"
    GUI = "gui"


class PromptOrLog:
    """Small helper to either prompt via a simple GUI or fall back to logging/console.

    Constructor signature:
        PromptOrLog(override_mode: Optional[Mode] = None)

    The single optional parameter is named `override_mode` (intentionally matching the
    user's requested spelling) and must be a member of the `Mode` enum or None. If
    None, the instance will decide the mode using internal auto-detection heuristics.
    """

    def __init__(self, override_mode: Optional[Mode] = None) -> None:
        if override_mode is not None and not isinstance(override_mode, Mode):
            raise TypeError("override_mode must be a Mode enum or None")
        self.override_mode = override_mode

    def get_mode(self) -> Mode:
        """Return the effective Mode for this instance.

        If `override_mode` was provided it is returned directly, otherwise an
        auto-detection is performed.
        """
        if self.override_mode is not None:
            return self.override_mode
        return self.__auto_detect_mode()

    @staticmethod
    def __auto_detect_mode() -> Mode:
        """Heuristic to choose between GUI and LOG when mode is AUTO_DETECT.

        Current heuristics (conservative):
        - If X11/Wayland DISPLAY is present, prefer GUI.
        - If running in a CI environment (common CI env vars), prefer LOG.
        - If stdout is a TTY, prefer LOG (interactive terminal use-case).
        - Default to LOG.
        """
        # GUI if a display server is present (X11/Wayland)
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return Mode.GUI

        # Common CI indicators -> non-interactive logging
        ci_vars = ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "TRAVIS")
        if any(os.environ.get(v) for v in ci_vars):
            return Mode.LOG

        # If stdout is a TTY, assume terminal interaction -> use LOG
        try:
            if sys.stdout.isatty():
                return Mode.LOG
        except Exception:
            # If any issue checking isatty, fall back to LOG
            return Mode.LOG

        return Mode.LOG

    def prompt(self, message: str, default: Optional[str] = None) -> Optional[str]:
        """Prompt the user for input according to the effective mode.

        - In LOG mode this prints the message and returns the default immediately.
          (This method does not block for console input to keep behavior simple.)
        - In GUI mode it attempts to open a simple tkinter dialog; if tkinter is not
          available or fails it falls back to LOG behavior.

        Returns the entered string in GUI mode (or None if cancelled), otherwise the
        provided default in LOG/fallback mode.
        """
        mode = self.get_mode()
        if mode == Mode.LOG:
            print(message)
            return default

        if mode == Mode.GUI:
            try:
                import tkinter as tk
                from tkinter import simpledialog
            except Exception:
                # Fall back to console behavior if tkinter isn't available
                print(message)
                return default

            # Ensure `answer` is defined even if the dialog fails unexpectedly
            answer: Optional[str] = default
            root = tk.Tk()
            root.withdraw()
            try:
                answer = simpledialog.askstring("Input", message, initialvalue=default)
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass
            return answer

        # Shouldn't reach here, but keep a safe default
        print(message)
        return default

    def dialog(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question and return True for yes, False for no.

        Behavior:
        - In GUI mode, show a simple yes/no dialog using tkinter.messagebox.askyesno
          and return the user's choice.
        - In LOG mode (or if GUI is unavailable) log the question and return the
          provided `default` value immediately (non-blocking).

        Args:
            question: The question to present to the user.
            default: The boolean value to return in LOG mode or if GUI can't be used.
        """
        mode = self.get_mode()
        if mode == Mode.LOG:
            LOG.info(question)
            return default

        if mode == Mode.GUI:
            try:
                import tkinter as tk
                from tkinter import messagebox
            except Exception:
                LOG.exception("tkinter not available; falling back to LOG behavior")
                LOG.info(question)
                return default

            try:
                root = tk.Tk()
                root.withdraw()
            except Exception:
                # If creating a root window fails, fall back
                LOG.exception("failed to initialize tkinter root; falling back to LOG")
                LOG.info(question)
                return default

            # Default result to `default` to ensure a value is always returned
            result: bool = bool(default)
            try:
                # askyesno returns True for yes, False for no
                result = messagebox.askyesno("Confirm", question)
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass

            return bool(result)

        # Default safe behaviour
        LOG.info(question)
        return default


__all__ = ["Mode", "PromptOrLog"]
