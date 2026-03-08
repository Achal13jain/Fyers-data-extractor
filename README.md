# Fyers MCX Downloader

A production-grade Command Line Interface (CLI) tool designed to download historical MCX Gold futures OHLCV data directly from the Fyers API v3. 

## Features
- **Data Chunking**: Automatically bypasses Fyers' 100-day limit per request by chunking queries.
- **Robust Retries**: Handles API failures gracefully using exponential backoff.
- **Continuous Contracts**: Configured to fetch continuous future contracts data (e.g., `MCX:GOLD25APRFUT`).
- **Smart Auth Flow**: Opens the browser for OAuth only when required. Caches valid tokens locally (`token.json`).

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- A Fyers Developer Account and trading account.

### 2. Create a Fyers API App
1. Go to the [Fyers API Dashboard](https://myapi.fyers.in/).
2. Create a new App.
3. Set the **Redirect URI** to `http://127.0.0.1:8080/`.
4. After creation, you'll receive your **App ID** (Client ID) and **Secret Key**.

### 3. Installation
1. Clone this repository (or copy the files).
2. Activate your virtual environment (if you haven't already):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 4. Configuration
1. Rename `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your credentials:
   ```env
   FYERS_CLIENT_ID=your_client_id_here
   FYERS_SECRET_KEY=your_secret_key_here
   FYERS_REDIRECT_URI=http://127.0.0.1:8080/
   LOG_LEVEL=INFO
   ```

## Usage

On your first run, the tool will open a browser window displaying the Fyers login page. Log in, and the browser will be redirected to your Redirect URI appended with an `auth_code`. Copy this `auth_code` and paste it into the CLI prompt.

### Example Commands

**Download 1-min data for the default Gold symbol from Jan 2024 to today:**
```bash
python main.py --from 2024-01-01
```

**Download with a custom symbol and output file:**
```bash
python main.py --symbol MCX:GOLD25JUNFUT --from 2024-06-01 --to 2024-09-30 --output gold_jun2024.csv
```

**Download 5-min data:**
```bash
python main.py --from 2024-01-01 --resolution 5
```

## Supported Resolutions
`1`, `2`, `3`, `5`, `10`, `15`, `20`, `30`, `60`, `120`, `240`, `1D`
