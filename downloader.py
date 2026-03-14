"""Data downloading logic for Fyers API."""

import time
from datetime import datetime
from typing import Optional

import pandas as pd
from fyers_apiv3 import fyersModel
from tqdm import tqdm

from config import FYERS_CLIENT_ID, FYERS_MAX_DAYS_PER_REQUEST
from utils import chunk_date_range, setup_logger
from auth import authenticate

logger = setup_logger(__name__)


class FyersDownloader:
    """Handles downloading historical data from Fyers.

    Can be initialized with an explicit access token (for web
    use) or without one (triggers CLI auth flow automatically).
    """

    def __init__(
        self, access_token: Optional[str] = None,
    ) -> None:
        """Initializes the Fyers Downloader.

        Args:
            access_token (Optional[str]): A pre-obtained Fyers
                access token. If None, triggers the CLI
                authenticate() flow (terminal input).
        """
        if access_token:
            self.access_token = access_token
        else:
            self.access_token = authenticate()

        self.fyers = fyersModel.FyersModel(
            client_id=FYERS_CLIENT_ID,
            is_async=False,
            token=self.access_token,
            log_path="",
        )

    def _fetch_chunk_with_retry(
        self,
        symbol: str,
        resolution: str,
        start_date: datetime,
        end_date: datetime,
        max_retries: int = 3
    ) -> Optional[list]:
        """Fetches a single chunk of data with retry logic.
        
        Args:
            symbol (str): The trading symbol.
            resolution (str): The timeframe resolution.
            start_date (datetime): The start date of the chunk.
            end_date (datetime): The end date of the chunk.
            max_retries (int): Maximum number of retry attempts.
            
        Returns:
            Optional[list]: A list of candles if successful, None otherwise.
        """
        data = {
            "symbol": symbol,
            "resolution": str(resolution),
            "date_format": "1",  # 1 indicates we're passing dates as yyyy-mm-dd
            "range_from": start_date.strftime("%Y-%m-%d"),
            "range_to": end_date.strftime("%Y-%m-%d"),
            "cont_flag": "1"  # 1 for continuous future contracts
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.fyers.history(data=data)
                
                if response.get("s") == "ok":
                    candles = response.get("candles", [])
                    logger.debug(
                        f"Fetched {len(candles)} rows for "
                        f"{data['range_from']} to {data['range_to']}."
                    )
                    return candles
                    
                logger.error(
                    f"Attempt {attempt}: API returned non-ok status: "
                    f"{response.get('message', response)}"
                )
            except Exception as e:
                logger.error(f"Attempt {attempt}: Exception during fetch: {e}")
                
            if attempt < max_retries:
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        logger.error(
            f"Failed to fetch data for {data['range_from']} to "
            f"{data['range_to']} after {max_retries} attempts."
        )
        return None

    def download_historical_data(
        self,
        symbol: str,
        resolution: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Downloads historical OHLCV data handling API constraints.
        
        Args:
            symbol (str): The trading symbol to download.
            resolution (str): The timeframe resolution (e.g., '1', '5', 'D').
            start_date (datetime): Beginning of the date range.
            end_date (datetime): End of the date range.
            
        Returns:
            pd.DataFrame: The compiled historical data.
        """
        logger.info(
            f"Starting download for {symbol} ({resolution} res) "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        chunks = chunk_date_range(
            start_date, end_date, FYERS_MAX_DAYS_PER_REQUEST
        )
        all_candles = []
        
        with tqdm(total=len(chunks), desc="Fetching Data Chunks") as pbar:
            for c_start, c_end in chunks:
                chunk_data = self._fetch_chunk_with_retry(
                    symbol, resolution, c_start, c_end
                )
                
                if chunk_data:
                    all_candles.extend(chunk_data)
                pbar.update(1)
                
        if not all_candles:
            logger.warning("No data was downloaded.")
            return pd.DataFrame()
            
        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        except Exception as e:
            logger.warning(f"Could not convert timestamp. Error: {e}")
            
        df.drop_duplicates(subset=["timestamp"], inplace=True)
        df.sort_values(by="timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        logger.info(f"Download complete. Total rows: {len(df)}")
        return df
