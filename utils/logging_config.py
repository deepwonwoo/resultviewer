import os
import logging
from utils.db_management import USER_RV_DIR, DEBUG


def setup_logger(debug_mode, log_file="application.log"):
    """Configure application logging."""

    level = logging.DEBUG if debug_mode else logging.INFO
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # Create console handler and set level to INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)

    # Create file handler and set level to DEBUG
    log_path = os.path.join(USER_RV_DIR, log_file)
    file_handler = logging.FileHandler(log_path, mode="w")
    file_handler.setLevel(level)
    # file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Configure logging for 'werkzeug' to minimize noise in the logs
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Initialize and configure the application logger

logger = setup_logger(debug_mode=DEBUG)
