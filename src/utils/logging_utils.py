import os
import logging
import time
import traceback
from functools import wraps
from dash import exceptions, ctx
from logging.handlers import RotatingFileHandler
from typing import Optional
from utils.db_management import USER_RV_DIR, DEBUG


class ResultViewerLogger:
    _instance: Optional["ResultViewerLogger"] = None

    def __init__(self, debug_mode: bool = DEBUG):
        self.logger = logging.getLogger("ResultViewer")
        self.logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels
        self.logger.handlers.clear()  # Clear existing handlers to avoid duplication

        self._setup_console_handler()
        self._setup_file_handler()

        # Ensure the logger doesn't propagate messages to the root logger
        self.logger.propagate = False

        # Suppress other loggers
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        logging.getLogger("dash").setLevel(logging.ERROR)

    @classmethod
    def get_instance(cls) -> "ResultViewerLogger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_console_handler(self):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Set console to INFO level
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self):
        log_file = os.path.join(USER_RV_DIR, "resultviewer.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setLevel(logging.DEBUG)  # Set file handler to DEBUG to capture all levels
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg, exc_info=True)

    def critical(self, msg: str):
        self.logger.critical(msg, exc_info=True)


# Global logger instance
logger = ResultViewerLogger.get_instance()


def debugging_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.info(f"{func.__name__} took {end - start:.2f}s to execute.")
            return result
        except Exception as e:
            logger.debug(f"Exception occurred in {func.__name__}: {str(e)}")
            logger.debug(f"{traceback.format_exc()}")
            raise

    return wrapper
