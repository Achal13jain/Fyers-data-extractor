"""Unit tests for utils.py — date chunking and logger setup."""

import logging
from datetime import datetime, timedelta

import pytest

from fyers_extractor.utils import chunk_date_range, setup_logger


class TestSetupLogger:
    """Verifies that setup_logger returns a functional logger."""

    def test_returns_logger_instance(self) -> None:
        """Logger returned matches the requested name."""
        log = setup_logger("test_logger")
        assert isinstance(log, logging.Logger)
        assert log.name == "test_logger"

    def test_no_duplicate_handlers(self) -> None:
        """Calling setup_logger twice on the same name must not
        add a second handler."""
        name = "dedup_test"
        log1 = setup_logger(name)
        handler_count = len(log1.handlers)
        log2 = setup_logger(name)
        assert log1 is log2
        assert len(log2.handlers) == handler_count


class TestChunkDateRange:
    """Verifies date-range chunking logic."""

    def test_single_day_range(self) -> None:
        """A 1-day range should return exactly one chunk."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 1)
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        assert len(chunks) == 1
        assert chunks[0] == (start, end)

    def test_range_within_single_chunk(self) -> None:
        """A range shorter than chunk_size should be one chunk."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 3, 1)   # 59 days
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        assert len(chunks) == 1
        assert chunks[0] == (start, end)

    def test_exact_boundary(self) -> None:
        """A range equal to chunk_size should be one chunk."""
        start = datetime(2025, 1, 1)
        end = start + timedelta(days=99)  # exactly 100 days
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        assert len(chunks) == 1
        assert chunks[0] == (start, end)

    def test_spans_multiple_chunks(self) -> None:
        """A 250-day range with chunk_size=100 should produce
        3 chunks: 100 + 100 + 50."""
        start = datetime(2025, 1, 1)
        end = start + timedelta(days=249)
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        assert len(chunks) == 3

    def test_chunks_are_contiguous(self) -> None:
        """Consecutive chunks should not have gaps or overlaps."""
        start = datetime(2025, 1, 1)
        end = start + timedelta(days=350)
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        for i in range(len(chunks) - 1):
            _, prev_end = chunks[i]
            next_start, _ = chunks[i + 1]
            assert next_start == prev_end + timedelta(days=1)

    def test_last_chunk_ends_on_end_date(self) -> None:
        """The final chunk must end exactly on the requested
        end_date."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 12, 31)
        chunks = chunk_date_range(start, end, chunk_size_days=100)
        assert chunks[-1][1] == end

    def test_custom_chunk_size(self) -> None:
        """Verify behaviour with a small custom chunk size."""
        start = datetime(2025, 6, 1)
        end = datetime(2025, 6, 10)   # 10 days
        chunks = chunk_date_range(start, end, chunk_size_days=3)
        # 3 + 3 + 3 + 1 = 4 chunks
        assert len(chunks) == 4
