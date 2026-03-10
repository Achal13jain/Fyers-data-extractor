"""Configuration constants for the Fyers MCX Downloader."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fyers API Credentials
FYERS_CLIENT_ID: str = os.getenv("FYERS_CLIENT_ID", "")
FYERS_SECRET_KEY: str = os.getenv("FYERS_SECRET_KEY", "")
FYERS_REDIRECT_URI: str = os.getenv("FYERS_REDIRECT_URI", "http://127.0.0.1:5000/")

# File Paths
TOKEN_FILE_PATH: str = "token.json"
DEFAULT_OUTPUT_FILE: str = "gold_1min.csv"

# API Constraints
FYERS_MAX_DAYS_PER_REQUEST: int = 100

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
