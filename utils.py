"""Utility functions for logging, date chunking, and general helpers."""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from config import LOG_LEVEL

def setup_logger(name: str) -> logging.Logger:
    """Sets up and returns a configured logger.
    
    Args:
        name (str): The name of the logger.
        
    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

def chunk_date_range(
    start_date: datetime,
    end_date: datetime,
    chunk_size_days: int = 100
) -> List[Tuple[datetime, datetime]]:
    """Chunks a date range into smaller intervals.
    
    Args:
        start_date (datetime): The start date of the entire range.
        end_date (datetime): The end date of the entire range.
        chunk_size_days (int): The maximum number of days per chunk.
        
    Returns:
        List[Tuple[datetime, datetime]]: A list of (start, end) date tuples.
    """
    chunks = []
    current_start = start_date
    
    while current_start <= end_date:
        current_end = current_start + timedelta(days=chunk_size_days - 1)
        if current_end > end_date:
            current_end = end_date
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
        
    return chunks
