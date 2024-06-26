import os
import logging
from logging.config import dictConfig
from dotenv import load_dotenv

# import from .env
load_dotenv()
DISCORD_API_TOKEN = os.getenv('DISCORD_TOKEN')
LLM_ADDRESS = os.getenv('LLM_ADDRESS')
IMG_ADDRESS = os.getenv('IMG_ADDRESS')

# logging
LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
        "standard": {"format": "%(levelname)-10s - %(name)-15s : %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "console2": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/infos.log",
            "mode": "a",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "bot": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "discord": {
            "handlers": ["console2", "file"],
            "level": "INFO",
            "propagate": False,
        },
    }
}

dictConfig(LOGGING_CONFIG)