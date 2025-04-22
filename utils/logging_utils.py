import os
import logging
from logging.handlers import RotatingFileHandler
from utils.config import CONFIG


def setup_logger():
    logger = logging.getLogger("ResultViewer")
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    log_file = os.path.join(CONFIG.USER_RV_DIR, "resultviewer.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    logger.addHandler(file_handler)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("dash").setLevel(logging.ERROR)

    return logger


logger = setup_logger()
