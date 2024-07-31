import logging
import os
import sys
from typing import Optional

FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)d %(message)s"
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


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


def _setup_default_logger(log_file: Optional[str] = None):
    global _default_handler
    if _default_handler is None:
        _default_handler = logging.StreamHandler(sys.stdout)
        _default_handler.flush = sys.stdout.flush  # type: ignore
        fmt = NewLineFormatter(FORMAT, datefmt=DATE_FORMAT)
        _default_handler.setFormatter(fmt)


_setup_default_logger()


def init_logger(name: str, log_file: Optional[str] = None):
    logger = logging.getLogger(name)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        fmt = NewLineFormatter(FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    else:
        global _default_handler
        logger.addHandler(_default_handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    return logger
