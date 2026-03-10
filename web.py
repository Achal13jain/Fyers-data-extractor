"""FastAPI Web Server for Fyers MCX Downloader."""

import os
import tempfile
import urllib.parse
from datetime import datetime

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from discovery import fetch_mcx_master, get_latest_gold_symbol
from downloader import FyersDownloader
from utils import setup_logger

logger = setup_logger(__name__)

VALID_RESOLUTIONS = {
    "1", "2", "3", "5", "10", "15",
    "20", "30", "60", "120", "240", "1D",
}

app = FastAPI(title="Fyers MCX Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static frontend files
os.makedirs("static", exist_ok=True)
app.mount(
    "/frontend",
    StaticFiles(directory="static", html=True),
    name="static",
)


class DownloadRequest(BaseModel):
    symbol: str
    resolution: str = "1"
    from_date: str
    to_date: str


def _cleanup_temp_file(path: str) -> None:
    """Removes a temporary file from disk after response is sent.

    Args:
        path (str): Absolute path to the temp file.
    """
    try:
        os.unlink(path)
    except OSError:
        logger.warning(f"Failed to clean up temp file: {path}")


@app.get("/")
def redirect_to_frontend():
    """Redirect root to frontend."""
    return RedirectResponse(url="/frontend/")


@app.get("/api/symbols")
def get_symbols(query: str = ""):
    """Returns top 50 symbols matching the query from Fyers master.

    Uses the cached master CSV fetcher to avoid redundant
    network downloads on every keystroke.
    """
    try:
        rows = fetch_mcx_master()
    except Exception as e:
        logger.error(f"Failed fetching symbols: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch symbols from Fyers API",
        )

    results = []
    query_upper = query.upper()

    for row in rows:
        sym_name = row["name"].upper()
        sym_fyers = row["symbol"]

        if not query_upper or query_upper in sym_name \
                or query_upper in sym_fyers:
            if "FUT" in sym_name:
                results.append({
                    "name": row["name"],
                    "symbol": sym_fyers,
                })
                if len(results) >= 50:
                    break

    return {"symbols": results}


@app.post("/api/download")
def download_data(
    req: DownloadRequest,
    background_tasks: BackgroundTasks,
):
    """API endpoint to download data given a date range."""
    # Validate resolution
    if req.resolution not in VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid resolution '{req.resolution}'. "
                f"Allowed: {', '.join(sorted(VALID_RESOLUTIONS))}."
            ),
        )

    # Parse dd-mm-yyyy dates
    try:
        start_date = datetime.strptime(req.from_date, "%d-%m-%Y")
        end_date = datetime.strptime(req.to_date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Expected DD-MM-YYYY.",
        )

    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be after end date.",
        )

    try:
        logger.info(
            f"Web request received: {req.symbol} "
            f"from {req.from_date} to {req.to_date}"
        )
        downloader = FyersDownloader()

        # If user explicitly selected 'auto' or 'gold',
        # use discovery fallback, else use exact passed symbol
        symbol = req.symbol
        if symbol.lower() in ["auto", "gold"]:
            symbol = get_latest_gold_symbol()

        df = downloader.download_historical_data(
            symbol=symbol,
            resolution=req.resolution,
            start_date=start_date,
            end_date=end_date,
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail="No data found for the selected date range.",
            )

        # Save to temp CSV and schedule cleanup after response
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv",
        )
        df.to_csv(tmp.name, index=False)
        tmp.close()
        background_tasks.add_task(_cleanup_temp_file, tmp.name)

        safe_sym = symbol.replace(":", "_")
        friendly_name = (
            f"{safe_sym}_{req.resolution}m_"
            f"{req.from_date}_to_{req.to_date}.csv"
        )
        friendly_name_encoded = urllib.parse.quote(friendly_name)

        return FileResponse(
            path=tmp.name,
            filename=friendly_name,
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename*=UTF-8''{friendly_name_encoded}"
                ),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting web server on http://127.0.0.1:8000")
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=True)
