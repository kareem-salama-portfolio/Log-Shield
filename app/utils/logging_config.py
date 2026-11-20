"""Configure the required local rotating application log."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(data_directory: str | Path) -> None:
    directory = Path(data_directory)
    directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(
        getattr(handler, "baseFilename", "").lower()
        == str(directory / "logshield.log").lower()
        for handler in root.handlers
    ):
        return
    handler = RotatingFileHandler(
        directory / "logshield.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.setLevel(logging.INFO)
    root.addHandler(handler)
