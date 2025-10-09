import logging
from typing import Type


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels for better readability."""

    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"  # Reset color code

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class Logger(logging.Logger):
    """Custom Logger class to initialize and configure loggers with colorized output."""

    def __new__(cls: Type["Logger"], name: str) -> "Logger":
        # Get a logger instance using logging.getLogger to ensure singleton pattern for the same name
        logger_level = logging.INFO

        logger = logging.getLogger(name)

        # Apply the configuration only if it hasn't been configured yet
        if not logger.hasHandlers():
            logger.setLevel(logger_level)
            handler = logging.StreamHandler()
            handler.setFormatter(
                ColoredFormatter(
                    "%(asctime)s %(name)s (%(filename)s:%(lineno)d) %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(handler)

        return logger