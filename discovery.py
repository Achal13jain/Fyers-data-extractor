"""Automatic symbol discovery from Fyers Symbol Master."""

import csv
import io
import urllib.request
from datetime import datetime

from utils import setup_logger

logger = setup_logger(__name__)

FYERS_MCX_COM_URL = "https://public.fyers.in/sym_details/MCX_COM.csv"

def get_latest_gold_symbol() -> str:
    """Downloads Fyers Symbol Master, prints top 5, and returns the nearest gold future.
    
    Returns:
        str: The Fyers trading symbol for the nearest Gold future.
    """
    logger.info("Downloading Fyers MCX Symbol Master...")
    req = urllib.request.Request(FYERS_MCX_COM_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            
        reader = csv.reader(io.StringIO(content))
        gold_futs = []
        for row in reader:
            if len(row) > 10:
                sym_name = row[1]
                sym_fyers = row[9]
                
                # Check that it's a standard GOLD minimum contract and a FUTures contract
                # Ignoring GOLDGUINEA, GOLDPETAL, GOLDM to just get main GOLD, 
                # but if we just check for exact start it might be "GOLD "
                if sym_name.upper().startswith("GOLD ") and "FUT" in sym_name.upper():
                    # Format e.g. 'GOLD 02 Apr 26 FUT'
                    # Or 'MCX:GOLD26APRFUT'
                    # We should parse expiry from column 7 (Unix epoch expiry time) if valid, 
                    # but Fyers row[7] is often yyyy-mm-dd or epoch.
                    # Column 7: '2026-03-07' is not expiry, column 8 is epoch expiry '1774376700'
                    try:
                        expiry_epoch = int(row[8])
                    except (ValueError, IndexError):
                        expiry_epoch = 9999999999
                        
                    gold_futs.append({
                        "name": sym_name,
                        "symbol": sym_fyers,
                        "expiry": expiry_epoch
                    })
                    
        if not gold_futs:
            logger.error("No active GOLD futures found in the master file.")
            raise ValueError("No GOLD futures found.")
            
        # Sort by expiry to find the nearest
        gold_futs.sort(key=lambda x: x["expiry"])
        
        logger.info("Top 5 Available GOLD Futures Contracts:")
        for i, gf in enumerate(gold_futs[:5], 1):
            # Print as requested by the user
            logger.info(f"  {i}. {gf['name']} -> {gf['symbol']}")
            
        selected = gold_futs[0]['symbol']
        logger.info(f"Auto-selected nearest contract: {selected}")
        return selected

    except Exception as e:
        logger.error(f"Failed to auto-discover symbol: {e}")
        raise
