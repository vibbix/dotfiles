from __future__ import annotations

from enum import Enum
from typing import Optional
import os
import sys
import logging
LOG = logging.getLogger(__name__)

GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk, simpledialog, messagebox
    GUI_AVAILABLE = True
except ImportError as e:
    LOG.error("tkinter not available; GUI mode will not be usable: %s", e)


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

        return Mode.GUI

    def prompt(self, message: str, default: Optional[str] = None) -> Optional[str]:
        """Prompt the user for input according to the effective mode.

        - In LOG mode this prints the message and prompts for console input.
        - In GUI mode it attempts to open a simple tkinter dialog; if tkinter is not
          available or fails it falls back to LOG behavior.

        Returns the entered string (or None if cancelled in GUI mode, or empty string
        is entered in console mode without a default).
        """
        mode = self.get_mode()
        if mode == Mode.LOG:
            if default:
                prompt_text = f"{message} [{default}]: "
            else:
                prompt_text = f"{message}: "
            try:
                user_input = input(prompt_text).strip()
                # If user pressed enter without typing, return default
                if not user_input and default:
                    return default
                # Return the user input (could be empty string)
                return user_input if user_input else None
            except (EOFError, KeyboardInterrupt):
                # Handle Ctrl+D or Ctrl+C gracefully
                print("\nCancelled by user")
                return None

        if mode == Mode.GUI:
            if not GUI_AVAILABLE:
                # Fall back to console behavior if tkinter isn't available
                return self.prompt(message, default)

            # Ensure `answer` is defined even if the dialog fails unexpectedly
            answer: Optional[str] = default
            try:
                root = tk.Tk()
                root.withdraw()
                try:
                    answer = simpledialog.askstring("Input", message, initialvalue=default)
                finally:
                    try:
                        root.destroy()
                    except Exception:
                        pass
            except Exception as e:
                LOG.exception("Failed to show GUI dialog, falling back to console: %s", e)
                # Fall back to console input
                if default:
                    prompt_text = f"{message} [{default}]: "
                else:
                    prompt_text = f"{message}: "
                try:
                    user_input = input(prompt_text).strip()
                    if not user_input and default:
                        return default
                    return user_input if user_input else None
                except (EOFError, KeyboardInterrupt):
                    print("\nCancelled by user")
                    return None
            return answer

        # Shouldn't reach here, but keep a safe default
        print(message)
        return default

    def dialog(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question and return True for yes, False for no.

        Behavior:
        - In GUI mode, show a simple yes/no dialog using tkinter.messagebox.askyesno
          and return the user's choice.
        - In LOG mode (or if GUI is unavailable) prompt via console for y/n input.

        Args:
            question: The question to present to the user.
            default: The boolean value to return as default if user just presses enter.
        """
        mode = self.get_mode()
        if mode == Mode.LOG:
            default_indicator = "Y/n" if default else "y/N"
            prompt_text = f"{question} [{default_indicator}]: "

            try:
                while True:
                    user_input = input(prompt_text).strip().lower()
                    # If empty input, use default
                    if not user_input:
                        return default
                    # Check for yes/no responses
                    if user_input in ('y', 'yes'):
                        return True
                    elif user_input in ('n', 'no'):
                        return False
                    else:
                        print("Please enter 'y' or 'n' (or press Enter for default)")
            except (EOFError, KeyboardInterrupt):
                # Handle Ctrl+D or Ctrl+C gracefully
                print("\nCancelled by user, using default")
                return default

        if mode == Mode.GUI:
            if not GUI_AVAILABLE:
                # Fall back to console behavior if tkinter isn't available
                default_indicator = "Y/n" if default else "y/N"
                prompt_text = f"{question} [{default_indicator}]: "

                try:
                    while True:
                        user_input = input(prompt_text).strip().lower()
                        if not user_input:
                            return default
                        if user_input in ('y', 'yes'):
                            return True
                        elif user_input in ('n', 'no'):
                            return False
                        else:
                            print("Please enter 'y' or 'n' (or press Enter for default)")
                except (EOFError, KeyboardInterrupt):
                    print("\nCancelled by user, using default")
                    return default

            # Default result to `default` to ensure a value is always returned
            result: bool = bool(default)
            try:
                root = tk.Tk()
                root.withdraw()
                try:
                    # askyesno returns True for yes, False for no
                    result = messagebox.askyesno("Confirm", question)
                finally:
                    try:
                        root.destroy()
                    except Exception:
                        pass
            except Exception as e:
                LOG.exception("Failed to show GUI dialog, falling back to console: %s", e)
                # Fall back to console input
                default_indicator = "Y/n" if default else "y/N"
                prompt_text = f"{question} [{default_indicator}]: "

                try:
                    while True:
                        user_input = input(prompt_text).strip().lower()
                        if not user_input:
                            return default
                        if user_input in ('y', 'yes'):
                            return True
                        elif user_input in ('n', 'no'):
                            return False
                        else:
                            print("Please enter 'y' or 'n' (or press Enter for default)")
                except (EOFError, KeyboardInterrupt):
                    print("\nCancelled by user, using default")
                    return default

            return bool(result)

        # Default safe behaviour
        LOG.info(question)
        return default


__all__ = ["Mode", "PromptOrLog"]
