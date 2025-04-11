import os
import logging
from logging.handlers import RotatingFileHandler
from utils.config import CONFIG


def setup_logger():
    # 기본 로거 설정
    logger = logging.getLogger("ResultViewer")
    logger.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    # 파일 핸들러
    log_file = os.path.join(CONFIG.USER_RV_DIR, "resultviewer.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    logger.addHandler(file_handler)

    # 다른 로거 억제
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("dash").setLevel(logging.ERROR)

    return logger


# 글로벌 로거 인스턴스
logger = setup_logger()
