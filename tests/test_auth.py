"""Unit tests for auth.py — token validation and persistence."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from auth import is_token_valid, load_saved_token, save_token


class TestIsTokenValid:
    """Verifies token-validity checks based on date comparison."""

    def test_valid_token_issued_today(self) -> None:
        """A token timestamped today should be valid."""
        data = {
            "access_token": "abc123",
            "timestamp": datetime.now().isoformat(),
        }
        assert is_token_valid(data) is True

    def test_expired_token_from_yesterday(self) -> None:
        """A token from yesterday should be invalid."""
        yesterday = datetime.now() - timedelta(days=1)
        data = {
            "access_token": "abc123",
            "timestamp": yesterday.isoformat(),
        }
        assert is_token_valid(data) is False

    def test_missing_timestamp_key(self) -> None:
        """Missing 'timestamp' key should return False."""
        assert is_token_valid({"access_token": "abc"}) is False

    def test_missing_access_token_key(self) -> None:
        """Missing 'access_token' key should return False."""
        assert is_token_valid({"timestamp": "2025-01-01"}) is False

    def test_corrupt_timestamp(self) -> None:
        """A non-ISO timestamp string should return False."""
        data = {
            "access_token": "abc",
            "timestamp": "not-a-date",
        }
        assert is_token_valid(data) is False

    def test_empty_dict(self) -> None:
        """An empty dict should return False."""
        assert is_token_valid({}) is False


class TestSaveAndLoadToken:
    """Integration tests for save_token and load_saved_token."""

    def test_round_trip(self, tmp_path) -> None:
        """Saving then loading a token should return
        the same access_token."""
        token_file = tmp_path / "token.json"
        with patch("auth.TOKEN_FILE_PATH", str(token_file)):
            save_token("my_secret_token")
            loaded = load_saved_token()
        assert loaded == "my_secret_token"

    def test_load_returns_none_when_file_missing(
        self, tmp_path,
    ) -> None:
        """load_saved_token should return None if no file exists."""
        token_file = tmp_path / "nonexistent.json"
        with patch("auth.TOKEN_FILE_PATH", str(token_file)):
            assert load_saved_token() is None

    def test_load_returns_none_for_expired_token(
        self, tmp_path,
    ) -> None:
        """A token saved yesterday should be treated as expired."""
        token_file = tmp_path / "token.json"
        yesterday = datetime.now() - timedelta(days=1)
        data = {
            "access_token": "old_token",
            "timestamp": yesterday.isoformat(),
        }
        token_file.write_text(json.dumps(data))
        with patch("auth.TOKEN_FILE_PATH", str(token_file)):
            assert load_saved_token() is None

    def test_load_returns_none_for_corrupt_json(
        self, tmp_path,
    ) -> None:
        """Corrupt JSON in token file should return None."""
        token_file = tmp_path / "token.json"
        token_file.write_text("{corrupt json!!!")
        with patch("auth.TOKEN_FILE_PATH", str(token_file)):
            assert load_saved_token() is None
