import logging
import os
import sys
import tkinter as tk
import traceback

from tkinter import messagebox
from typing import Callable, TypeVar, ParamSpec, Optional, Optional, Concatenate


_T = TypeVar("_T")
_T2 = TypeVar("_T2")
_P = ParamSpec("_P")


def setup_logging(file: Optional[str] = None, debug: Optional[bool] = None):
    if debug is None:
        debug = "--debug" in sys.argv
    if file and not os.path.exists(os.path.dirname(file)):
        os.makedirs(os.path.dirname(file))
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(_ColourFormatter())
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(handler)
    if file:
        fileHandler = logging.FileHandler(file, "w", "UTF-8")
        fileHandler.setFormatter(_ColourFormatter())
        logger.addHandler(fileHandler)


# THIS CLASS IS FROM DISCORD.PY (https://github.com/Rapptz/discord.py)
class _ColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[0m %(message)s')
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output
    
def log_critical(func: Callable[_P, _T]) -> Callable[_P, Optional[_T]]:
    """Logs crashes and exits"""
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Optional[_T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            message = "\n".join(traceback.format_exception(e))
            message = e.__class__.__name__ + "\n\n" + message
            logging.critical(message)
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Neuro 21 Station Player Crashed!",
                "Neuro 21 Station Player encountered a critical exception and cannot continue.",
                detail='\n'.join(message.splitlines()[-5:])
                )
            root.destroy()
    return wrapper

def log_error(func: Callable[_P, _T]) -> Callable[_P, Optional[_T]]:
    """Logs crashes and returns None instead of crashing"""
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Optional[_T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            message = "\n".join(traceback.format_exception(e))
            message = e.__class__.__name__ + "\n\n" + message
            logging.error(message)
    return wrapper

def cleanup(cleaner: Callable[Concatenate[_T, _P], _T2]) -> Callable[[Callable[_P, _T]], Callable[_P, _T2]]:
    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T2]:
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T2:
            return cleaner(func(*args, **kwargs), *args, **kwargs)
        return wrapper
    return decorator