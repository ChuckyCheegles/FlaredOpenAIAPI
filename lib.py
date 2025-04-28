import logging
from logging.handlers import RotatingFileHandler
import config
import re

logger = logging.getLogger(__name__)

# Configure rotating file handler
rotating_handler = RotatingFileHandler(
    filename=config.Log_File,
    maxBytes=config.Max_Log_Size,  # Maximum file size before rotation (e.g., 1000000 bytes = 1MB)
    encoding='utf-8'
)
rotating_handler.setLevel(logging.INFO)

# Use the same format as logging.basicConfig's default
formatter = logging.Formatter(logging.BASIC_FORMAT)
rotating_handler.setFormatter(formatter)

# Apply the handler to the root logger
root_logger = logging.getLogger()
root_logger.addHandler(rotating_handler)
root_logger.setLevel(logging.INFO)

def clean_ansi(text):
    ansi_escape = re.compile(r'''
        \x1B          # ESC (hex 1B)
        (?:           # Start a non-capturing group
            [@-Z\\-_] # Match single-character ANSI codes (e.g., ESCc)
        |             # OR
            \[        # CSI (Control Sequence Introducer) starting with "["
            [0-?]*    # Optional parameters (0x30–0x3F)
            [ -/]*    # Optional intermediate bytes (0x20–0x2F)
            [@-~]     # Final byte (0x40–0x7E, e.g., 'm' for style codes)
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', text)

def log(text):
    cleaned_text = clean_ansi(text)
    print(text)
    logger.info(cleaned_text)