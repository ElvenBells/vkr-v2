import pytest
import json
import os
from pathlib import Path
from loguru import logger

@pytest.fixture(scope="session")
def config():
    config_path = Path("configs/config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session", autouse=True)
def setup_logging(config):
    logger.remove()
    logger.add(sys.stderr, level=config["experiment"]["log_level"], 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    yield