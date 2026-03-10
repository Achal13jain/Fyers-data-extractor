"""Unit tests for discovery.py — CSV caching and gold symbol logic."""

from unittest.mock import MagicMock, patch

import pytest

from discovery import fetch_mcx_master, get_latest_gold_symbol, _master_cache


# A minimal CSV snippet that mimics the Fyers MCX master format.
# Columns: 0=id, 1=name, 2-7=various, 8=expiry_epoch, 9=fyers_symbol, 10+=extra
MOCK_CSV = (
    "1,GOLD 04 Apr 26 FUT,X,X,X,X,X,X,1743724200,MCX:GOLD26APRFUT,extra\n"
    "2,GOLD 05 Jun 26 FUT,X,X,X,X,X,X,1749110400,MCX:GOLD26JUNFUT,extra\n"
    "3,GOLDGUINEA 04 Apr 26 FUT,X,X,X,X,X,X,1743724200,MCX:GOLDGUINEA26APRFUT,extra\n"
    "4,SILVER 05 May 26 FUT,X,X,X,X,X,X,1746403200,MCX:SILVER26MAYFUT,extra\n"
    "5,CRUDEOIL 19 Mar 26 FUT,X,X,X,X,X,X,1742342400,MCX:CRUDEOIL26MARFUT,extra\n"
)


def _reset_cache() -> None:
    """Clears the in-memory master cache between tests."""
    _master_cache["rows"] = None
    _master_cache["fetched_at"] = 0.0


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure every test starts with a fresh cache."""
    _reset_cache()
    yield
    _reset_cache()


def _mock_urlopen(csv_content: str) -> MagicMock:
    """Creates a mock urllib.request.urlopen context manager."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = csv_content.encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestFetchMcxMaster:
    """Verifies the cached CSV fetcher."""

    @patch("discovery.urllib.request.urlopen")
    def test_returns_parsed_rows(self, mock_open) -> None:
        """Should return all rows from the CSV."""
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        rows = fetch_mcx_master()
        assert len(rows) == 5
        assert rows[0]["name"] == "GOLD 04 Apr 26 FUT"
        assert rows[0]["symbol"] == "MCX:GOLD26APRFUT"

    @patch("discovery.urllib.request.urlopen")
    def test_cache_prevents_second_download(
        self, mock_open,
    ) -> None:
        """Second call within TTL should use cache, not network."""
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        fetch_mcx_master()
        fetch_mcx_master()
        # urlopen should only be called once
        assert mock_open.call_count == 1

    @patch("discovery.urllib.request.urlopen")
    def test_cache_expires(self, mock_open) -> None:
        """After TTL expires, the CSV should be re-fetched."""
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        fetch_mcx_master()
        # Manually expire the cache
        _master_cache["fetched_at"] = 0.0
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        fetch_mcx_master()
        assert mock_open.call_count == 2


class TestGetLatestGoldSymbol:
    """Verifies Gold-specific auto-discovery."""

    @patch("discovery.urllib.request.urlopen")
    def test_selects_nearest_gold_future(
        self, mock_open,
    ) -> None:
        """Should return the Gold contract with the earliest
        expiry epoch."""
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        symbol = get_latest_gold_symbol()
        # GOLD Apr (1743724200) is earlier than GOLD Jun
        assert symbol == "MCX:GOLD26APRFUT"

    @patch("discovery.urllib.request.urlopen")
    def test_excludes_goldguinea(self, mock_open) -> None:
        """GOLDGUINEA should not match the 'GOLD ' prefix
        filter."""
        mock_open.return_value = _mock_urlopen(MOCK_CSV)
        symbol = get_latest_gold_symbol()
        assert "GUINEA" not in symbol

    @patch("discovery.urllib.request.urlopen")
    def test_raises_when_no_gold_found(
        self, mock_open,
    ) -> None:
        """Should raise ValueError if no GOLD FUT rows exist."""
        no_gold_csv = (
            "1,SILVER 05 May 26 FUT,X,X,X,X,X,X,"
            "1746403200,MCX:SILVER26MAYFUT,extra\n"
        )
        mock_open.return_value = _mock_urlopen(no_gold_csv)
        with pytest.raises(ValueError, match="No GOLD futures"):
            get_latest_gold_symbol()
