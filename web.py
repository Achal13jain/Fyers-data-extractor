"""FastAPI Web Server for Fyers MCX Downloader."""

import os
import tempfile
import urllib.parse
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from downloader import FyersDownloader
from discovery import get_latest_gold_symbol
from utils import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Fyers MCX Downloader API")

# Serve the static frontend files
os.makedirs("static", exist_ok=True)
app.mount("/frontend", StaticFiles(directory="static", html=True), name="static")

class DownloadRequest(BaseModel):
    symbol: str
    from_date: str
    to_date: str

@app.get("/")
def redirect_to_frontend():
    """Redirect root to frontend."""
    return RedirectResponse(url="/frontend/")

@app.get("/api/symbols")
def get_symbols(query: str = ""):
    """Returns top 20 symbols matching the query from Fyers master."""
    import urllib.request
    import csv
    import io
    
    url = "https://public.fyers.in/sym_details/MCX_COM.csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            
        reader = csv.reader(io.StringIO(content))
        results = []
        query_upper = query.upper()
        
        for row in reader:
            if len(row) > 10:
                sym_name = row[1].upper()
                sym_fyers = row[9]
                
                if not query_upper or query_upper in sym_name or query_upper in sym_fyers:
                    # Ignore options to keep list clean, or let them through? 
                    # Usually people want FUT. Let's just return basic info.
                    if "FUT" in sym_name:
                        results.append({
                            "name": row[1],
                            "symbol": sym_fyers
                        })
                        if len(results) >= 50: # Limit to top 50 matches
                            break
        return {"symbols": results}
    except Exception as e:
        logger.error(f"Failed fetching symbols: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch symbols from Fyers API")

@app.post("/api/download")
def download_data(req: DownloadRequest):
    """API endpoint to download data given a date range."""
    # Parse dd-mm-yyyy dates
    try:
        start_date = datetime.strptime(req.from_date, "%d-%m-%Y")
        end_date = datetime.strptime(req.to_date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Expected DD-MM-YYYY."
        )

    if start_date > end_date:
        raise HTTPException(
            status_code=400, 
            detail="Start date cannot be after end date."
        )

    try:
        logger.info(f"Web request received: {req.symbol} from {req.from_date} to {req.to_date}")
        downloader = FyersDownloader()
        
        # If user explicitly selected 'auto' or 'gold', use discovery fallback, 
        # else use exact passed symbol 
        symbol = req.symbol
        if symbol.lower() in ["auto", "gold"]:
            symbol = get_latest_gold_symbol()

        df = downloader.download_historical_data(
            symbol=symbol,
            resolution="1",
            start_date=start_date,
            end_date=end_date
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404, 
                detail="No data found for the selected date range."
            )

        # Save to temp CSV
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        df.to_csv(tmp.name, index=False)
        tmp.close()

        safe_sym = symbol.replace(":", "_")
        friendly_name = f"{safe_sym}_1min_{req.from_date}_to_{req.to_date}.csv"
        # URL encode the filename to prevent header parsing issues
        friendly_name_encoded = urllib.parse.quote(friendly_name)

        return FileResponse(
            path=tmp.name,
            filename=friendly_name,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{friendly_name_encoded}"
            }
        )

    except Exception as e:
        logger.error(f"Web download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting web server on http://127.0.0.1:8000")
    uvicorn.run("web:app", host="127.0.0.1", port=8000, reload=True)
