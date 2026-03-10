"""Automatic symbol discovery from Fyers Symbol Master.

Provides a cached CSV fetcher and a Gold-specific
auto-discovery utility used by both the CLI and Web API.
"""

import csv
import io
import time
import urllib.error
import urllib.request
from typing import Dict, List

from utils import setup_logger

logger = setup_logger(__name__)

FYERS_MCX_COM_URL = "https://public.fyers.in/sym_details/MCX_COM.csv"
_CACHE_TTL_SECONDS = 3600

# In-memory cache for the parsed master CSV rows
_master_cache: Dict[str, object] = {
    "rows": None,
    "fetched_at": 0.0,
}


def fetch_mcx_master() -> List[Dict[str, str]]:
    """Downloads and caches the Fyers MCX Symbol Master CSV.

    Returns a list of dicts with 'name', 'symbol', and 'expiry'
    keys. Results are cached in memory for up to 1 hour.

    Returns:
        List[Dict[str, str]]: Parsed rows from the master CSV.

    Raises:
        urllib.error.URLError: If the network request fails.
        ValueError: If the CSV cannot be parsed.
    """
    now = time.time()
    if (
        _master_cache["rows"] is not None
        and now - _master_cache["fetched_at"] < _CACHE_TTL_SECONDS
    ):
        return _master_cache["rows"]

    logger.info("Downloading Fyers MCX Symbol Master...")
    req = urllib.request.Request(
        FYERS_MCX_COM_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode("utf-8")

    reader = csv.reader(io.StringIO(content))
    rows: List[Dict[str, str]] = []

    for row in reader:
        if len(row) > 10:
            try:
                expiry_epoch = int(row[8])
            except (ValueError, IndexError):
                expiry_epoch = 9999999999

            rows.append({
                "name": row[1],
                "symbol": row[9],
                "expiry": expiry_epoch,
            })

    _master_cache["rows"] = rows
    _master_cache["fetched_at"] = time.time()
    logger.info(
        f"Symbol master cached. Total rows parsed: {len(rows)}"
    )
    return rows


def get_latest_gold_symbol() -> str:
    """Returns the nearest active Gold futures contract symbol.

    Parses the cached master CSV to find GOLD FUT contracts,
    sorts them by expiry, and returns the nearest one.

    Returns:
        str: The Fyers trading symbol for the nearest Gold future.

    Raises:
        urllib.error.URLError: If the CSV download fails.
        ValueError: If no Gold futures are found.
    """
    try:
        rows = fetch_mcx_master()
    except urllib.error.URLError as e:
        logger.error(f"Network error fetching symbol master: {e}")
        raise
    except ValueError as e:
        logger.error(f"Parse error in symbol master: {e}")
        raise

    gold_futs = [
        r for r in rows
        if r["name"].upper().startswith("GOLD ")
        and "FUT" in r["name"].upper()
    ]

    if not gold_futs:
        logger.error(
            "No active GOLD futures found in the master file."
        )
        raise ValueError("No GOLD futures found.")

    gold_futs.sort(key=lambda x: x["expiry"])

    logger.info("Top 5 Available GOLD Futures Contracts:")
    for i, gf in enumerate(gold_futs[:5], 1):
        logger.info(f"  {i}. {gf['name']} -> {gf['symbol']}")

    selected = gold_futs[0]["symbol"]
    logger.info(f"Auto-selected nearest contract: {selected}")
    return selected
