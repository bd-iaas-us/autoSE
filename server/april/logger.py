import logging
import os
from typing import Optional
import sys


_FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)d] %(message)s"

_DATE_FORMAT = "%m-%d %H:%M:%S"


class NewLineFormatter(logging.Formatter):
    """Adds logging prefix to newlines to align multi-line messages."""

    def __init__(self, fmt, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        msg = logging.Formatter.format(self, record)
        if record.message != "":
            parts = msg.split(record.message)
            msg = msg.replace("\n", "\r\n" + parts[0])
        return msg
    
_default_handler: Optional[logging.Handler] = None

def _setup_logger():
    global _default_handler
    if _default_handler is None:
        _default_handler = logging.StreamHandler(sys.stdout)
        _default_handler.flush = sys.stdout.flush  # type: ignore
        _default_handler.setLevel(logging.INFO)
        fmt = NewLineFormatter(_FORMAT, datefmt=_DATE_FORMAT)
        _default_handler.setFormatter(fmt)

_setup_logger()


def init_logger(name: str):
    global _default_handler
    logger = logging.getLogger(name)
    logger.addHandler(_default_handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))
    return logger