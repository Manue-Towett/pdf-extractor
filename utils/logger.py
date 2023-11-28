import logging
from typing import Optional

class Logger:
    """Logs info, warning and error messages"""
    def __init__(self, name: Optional[str]=None) -> None:
        name = __class__.__name__ if name is None else name

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        fmt = logging.Formatter("%(name)s:%(levelname)s - %(message)s")

        s_handler = logging.StreamHandler()
        s_handler.setLevel(logging.INFO)
        s_handler.setFormatter(fmt)

        f_handler = logging.FileHandler("./logs/logs.log", "w")
        f_handler.setLevel(logging.INFO)
        f_handler.setFormatter(fmt)

        [self.logger.addHandler(hdlr) for hdlr in [s_handler, f_handler]]

    def info(self, message: str) -> None:
        self.logger.info(message)
    
    def warn(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message, exc_info=True)