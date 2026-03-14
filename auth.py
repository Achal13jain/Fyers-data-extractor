"""Authentication module for Fyers API.

Provides both a CLI-friendly flow (terminal input) and a
web-friendly flow (URL generation + code exchange) for
obtaining Fyers OAuth access tokens.
"""

import json
import os
import webbrowser
from datetime import datetime
from typing import Optional

from fyers_apiv3 import fyersModel

from config import (
    FYERS_CLIENT_ID,
    FYERS_SECRET_KEY,
    FYERS_REDIRECT_URI,
    TOKEN_FILE_PATH,
)
from utils import setup_logger

logger = setup_logger(__name__)


def _validate_credentials() -> None:
    """Checks that API credentials are configured.

    Raises:
        ValueError: If client_id or secret_key is missing.
    """
    if not FYERS_CLIENT_ID or not FYERS_SECRET_KEY:
        raise ValueError(
            "FYERS_CLIENT_ID and FYERS_SECRET_KEY must be "
            "set in .env file."
        )


def _build_session() -> fyersModel.SessionModel:
    """Creates a Fyers SessionModel for OAuth flows.

    Returns:
        fyersModel.SessionModel: A configured session.
    """
    return fyersModel.SessionModel(
        client_id=FYERS_CLIENT_ID,
        secret_key=FYERS_SECRET_KEY,
        redirect_uri=FYERS_REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
    )


def is_token_valid(token_data: dict) -> bool:
    """Checks if the saved token is still valid (issued today).

    Args:
        token_data (dict): The token data dictionary.

    Returns:
        bool: True if valid, False otherwise.
    """
    if "timestamp" not in token_data \
            or "access_token" not in token_data:
        return False

    try:
        saved_date = datetime.fromisoformat(
            token_data["timestamp"]
        ).date()
        return saved_date == datetime.now().date()
    except (ValueError, TypeError):
        return False


def load_saved_token() -> Optional[str]:
    """Loads a saved token from disk if it exists and is valid.

    Returns:
        Optional[str]: The access token if valid, otherwise None.
    """
    if not os.path.exists(TOKEN_FILE_PATH):
        return None

    try:
        with open(TOKEN_FILE_PATH, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        if is_token_valid(token_data):
            logger.info("Found valid existing access token.")
            return token_data["access_token"]
        else:
            logger.info("Existing token is expired or invalid.")
    except Exception as e:
        logger.error(f"Failed to read token file: {e}")

    return None


def save_token(access_token: str) -> None:
    """Saves the access token to disk with the current timestamp.

    Args:
        access_token (str): The Fyers access token.
    """
    token_data = {
        "access_token": access_token,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=4)
        logger.info(
            f"Token saved successfully to {TOKEN_FILE_PATH}."
        )
    except Exception as e:
        logger.error(
            f"Failed to save token to {TOKEN_FILE_PATH}: {e}"
        )


# --- Web-Friendly Auth Functions ---

def generate_auth_url() -> str:
    """Generates the Fyers OAuth login URL without blocking.

    Used by the web server to redirect users to the Fyers
    login page in-browser, instead of requiring terminal input.

    Returns:
        str: The full Fyers OAuth authorization URL.

    Raises:
        ValueError: If API credentials are not configured.
    """
    _validate_credentials()
    session = _build_session()
    auth_url = session.generate_authcode()
    logger.info(f"Generated auth URL for web OAuth flow.")
    return auth_url


def exchange_auth_code(auth_code: str) -> str:
    """Exchanges an OAuth auth code for an access token.

    Completes the OAuth flow by sending the auth code to
    Fyers, receiving an access token, and persisting it
    to disk.

    Args:
        auth_code (str): The auth code from the OAuth redirect.

    Returns:
        str: The newly generated access token.

    Raises:
        ValueError: If credentials are missing or code is empty.
        RuntimeError: If Fyers rejects the auth code.
    """
    _validate_credentials()

    if not auth_code:
        raise ValueError("Auth code cannot be empty.")

    session = _build_session()
    session.set_token(auth_code)

    try:
        response = session.generate_token()
    except Exception as e:
        raise RuntimeError(
            f"Failed to generate token from auth code: {e}"
        )

    if response.get("s") != "ok":
        error_msg = response.get(
            "message", "Unknown error generating token."
        )
        raise RuntimeError(f"Fyers API Error: {error_msg}")

    access_token = response.get("access_token")
    if not access_token:
        raise RuntimeError(
            "Access token not found in the response."
        )

    logger.info("Successfully generated new access token.")
    save_token(access_token)
    return access_token


# --- CLI-Only Auth Function ---

def authenticate() -> str:
    """Authenticates with Fyers via terminal input (CLI only).

    If a valid token exists on disk, it is returned. Otherwise,
    opens a browser and waits for the user to paste the auth
    code into the terminal.

    Returns:
        str: The valid access token.

    Raises:
        ValueError: If client_id or secret_key is missing.
        RuntimeError: If authentication fails.
    """
    token = load_saved_token()
    if token:
        return token

    logger.info("Starting new authentication flow...")

    auth_url = generate_auth_url()
    print("=" * 80)
    print("Fyers Authentication Required")
    print("=" * 80)
    print(f"Opening browser to: {auth_url}")
    print(
        "Please log in, then copy the 'auth_code' parameter "
        "from the redirected URL."
    )
    print("=" * 80)

    webbrowser.open(auth_url)

    auth_code = input("Enter the auth_code here: ").strip()
    return exchange_auth_code(auth_code)
