"""Entry point for the Fyers MCX Downloader CLI."""

import argparse
import sys
from datetime import datetime

from config import DEFAULT_OUTPUT_FILE
from discovery import get_latest_gold_symbol
from downloader import FyersDownloader
from utils import setup_logger

VALID_RESOLUTIONS = {
    "1", "2", "3", "5", "10", "15",
    "20", "30", "60", "120", "240", "1D",
}

logger = setup_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments.
    
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Fyers MCX Historical Data Downloader CLI"
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        default="auto",
        help="The trading symbol (default: 'auto' to auto-detect nearest Gold Future)"
    )
    
    parser.add_argument(
        "--from",
        dest="from_date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--to",
        dest="to_date",
        type=str,
        default=datetime.today().strftime("%Y-%m-%d"),
        help="End date in YYYY-MM-DD format (default: today)"
    )
    
    parser.add_argument(
        "--resolution",
        type=str,
        default="1",
        help="Timeframe resolution (default: 1)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output file path (default: {DEFAULT_OUTPUT_FILE})"
    )
    
    return parser.parse_args()

def main() -> None:
    """Main function to run the CLI tool."""
    args = parse_arguments()
    
    try:
        start_date = datetime.strptime(args.from_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.to_date, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Invalid date format. Expected YYYY-MM-DD. Details: {e}")
        sys.exit(1)
        
    if start_date > end_date:
        logger.error("Start date cannot be after end date.")
        sys.exit(1)

    if args.resolution not in VALID_RESOLUTIONS:
        logger.error(
            f"Invalid resolution '{args.resolution}'. "
            f"Allowed: {', '.join(sorted(VALID_RESOLUTIONS))}"
        )
        sys.exit(1)
        
    try:
        downloader = FyersDownloader()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)
        
    symbol = args.symbol
    if symbol.lower() == "auto":
        try:
            logger.info("Auto-detecting nearest Fyers matching Gold Future...")
            symbol = get_latest_gold_symbol()
        except Exception as e:
            logger.error(f"Failed to auto-detect symbol: {e}")
            sys.exit(1)

    try:
        df = downloader.download_historical_data(
            symbol=symbol,
            resolution=args.resolution,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Download process failed: {e}")
        sys.exit(1)
        
    if not df.empty:
        try:
            df.to_csv(args.output, index=False)
            logger.info("=" * 60)
            logger.info("SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Symbol:       {symbol}")
            logger.info(f"Resolution:   {args.resolution}")
            logger.info(f"Date Range:   {start_date.date()} to {end_date.date()}")
            logger.info(f"Total Rows:   {len(df)}")
            logger.info(f"Output File:  {args.output}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Failed to save data to CSV: {e}")
            sys.exit(1)
    else:
        logger.warning(
            "Final dataframe is empty. "
            "No output file was created."
        )

if __name__ == "__main__":
    main()
