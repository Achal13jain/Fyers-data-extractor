"""FastAPI Web Server for Fyers MCX Downloader.

Provides a browser-based interface for downloading historical
MCX data, with a fully web-based OAuth callback flow that
eliminates the need for terminal interaction.
"""

import os
import tempfile
import urllib.parse
from datetime import datetime

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fyers_extractor.auth import (
    exchange_auth_code,
    generate_auth_url,
    load_saved_token,
)
from fyers_extractor.config import FYERS_CLIENT_ID
from fyers_extractor.discovery import fetch_mcx_master, get_latest_gold_symbol
from fyers_extractor.downloader import FyersDownloader
from fyers_extractor.utils import setup_logger

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
    """Request body for the download endpoint."""

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


# --- Auth Endpoints ---

@app.get("/api/auth/status")
def auth_status() -> dict:
    """Returns whether a valid Fyers token exists.

    The frontend polls this on page load to show the
    authentication status badge.
    """
    token = load_saved_token()
    return {"authenticated": token is not None}


@app.get("/api/auth/callback")
def auth_callback(
    s: str = "",
    code: str = "",
    auth_code: str = "",
    state: str = "",
) -> HTMLResponse:
    """OAuth callback endpoint that Fyers redirects to.

    After a successful Fyers login, the browser is redirected
    here with the auth code. This endpoint exchanges it for
    an access token and then redirects back to the main UI.

    Args:
        s: Status from Fyers (usually 'ok').
        code: The OAuth authorization code from Fyers.
        auth_code: Alternative param name for the auth code.
        state: OAuth state parameter (unused).
    """
    # Fyers may send the code as 'auth_code' or 'code'.
    # We prioritize 'auth_code' because 'code' sometimes contains
    # status codes (like '200') instead of the actual token.
    final_code = auth_code or code

    if not final_code:
        return HTMLResponse(
            content=_auth_result_page(
                success=False,
                message="No auth code received from Fyers.",
            ),
            status_code=400,
        )

    try:
        exchange_auth_code(final_code)
        logger.info("Web OAuth callback: token saved.")
        return HTMLResponse(
            content=_auth_result_page(
                success=True,
                message="Authentication successful!",
            ),
        )
    except (ValueError, RuntimeError) as e:
        logger.error(f"OAuth callback failed: {e}")
        return HTMLResponse(
            content=_auth_result_page(
                success=False,
                message=str(e),
            ),
            status_code=400,
        )


def _auth_result_page(success: bool, message: str) -> str:
    """Generates a minimal HTML page for the OAuth result.

    Shows a success or error message and auto-redirects
    back to the main frontend after 2 seconds.

    Args:
        success (bool): Whether authentication succeeded.
        message (str): The message to display to the user.

    Returns:
        str: HTML page content.
    """
    icon = "✅" if success else "❌"
    color = "#059669" if success else "#ef4444"
    redirect = "/frontend/?auth=success" if success else "#"
    auto_redirect = (
        f'<meta http-equiv="refresh" '
        f'content="2;url={redirect}">'
        if success else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">
    {auto_redirect}
    <title>Fyers Auth</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?\
family=Outfit:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: #f8fafc;
            margin: 0;
        }}
        .card {{
            text-align: center;
            background: white;
            padding: 48px;
            border-radius: 20px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            max-width: 400px;
        }}
        .icon {{ font-size: 3rem; margin-bottom: 16px; }}
        .msg {{
            color: {color};
            font-size: 1.2rem;
            font-weight: 600;
        }}
        .sub {{
            color: #64748b;
            margin-top: 12px;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <div class="msg">{message}</div>
        <div class="sub">
            {"Redirecting back to the app..."
             if success else
             "Please close this tab and try again."}
        </div>
    </div>
</body>
</html>"""


# --- Core Endpoints ---

@app.get("/")
def redirect_to_frontend() -> RedirectResponse:
    """Redirect root to frontend."""
    return RedirectResponse(url="/frontend/")


@app.get("/api/symbols")
def get_symbols(query: str = "") -> dict:
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
) -> FileResponse:
    """API endpoint to download data given a date range.

    If the Fyers token is expired, returns a 401 response
    with the OAuth login URL instead of blocking the server.
    """
    # Validate resolution
    if req.resolution not in VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid resolution '{req.resolution}'. "
                f"Allowed: "
                f"{', '.join(sorted(VALID_RESOLUTIONS))}."
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

    # Check auth before attempting download
    access_token = load_saved_token()
    if not access_token:
        try:
            auth_url = generate_auth_url()
        except ValueError as e:
            raise HTTPException(
                status_code=500, detail=str(e),
            )
        raise HTTPException(
            status_code=401,
            detail={
                "status": "auth_required",
                "auth_url": auth_url,
                "message": (
                    "Fyers token expired. "
                    "Please authenticate first."
                ),
            },
        )

    try:
        logger.info(
            f"Web request received: {req.symbol} "
            f"from {req.from_date} to {req.to_date}"
        )
        downloader = FyersDownloader(access_token=access_token)

        # Auto-detect Gold symbol if user requests it
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
                detail="No data found for the selected "
                       "date range.",
            )

        # Save to temp CSV and schedule cleanup
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
        friendly_name_encoded = urllib.parse.quote(
            friendly_name,
        )

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
    logger.info(
        "Starting web server on http://127.0.0.1:8000"
    )
    uvicorn.run(
        "web:app", host="127.0.0.1", port=8000, reload=True,
    )
