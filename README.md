# Fyers MCX Data Extractor

A beautiful, production-grade tool designed to download historical MCX futures OHLCV data directly from the Fyers API v3. 

It features both a robust **Command Line Interface (CLI)** and a gorgeous **Web UI** built with FastAPI and Vanilla JS.

![MCX Extractor UI Demo](https://img.shields.io/badge/UI-Glassmorphism-blue)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **Beautiful Web Interface**: A modern, interactive web portal that makes downloading data as simple as point-and-click.
- **Smart Symbol Auto-Discovery**: Automatically parses the live Fyers MCX Master CSV to search, dropdown, or auto-detect active continuous future contracts (e.g., `MCX:CRUDEOIL26MARFUT`).
- **Data Chunking**: Automatically bypasses Fyers' 100-day limit per request by securely chunking dates behind the scenes.
- **Robust Retries**: Handles API rate-limiting and connection failures gracefully using exponential backoff.
- **Smart Auth Flow**: Opens the browser for OAuth only when required. Caches valid tokens locally in `token.json` so you stay logged in.

---

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.9+
- A [Fyers Developer Account](https://myapi.fyers.in/) and a live trading account.

### 2. Create a Fyers API App
1. Go to the [Fyers API Dashboard](https://myapi.fyers.in/).
2. Create a new App.
3. Set the **Redirect URI** to `http://127.0.0.1:5000/`.
4. After creation, copy your **App ID** (Client ID) and **Secret Key**.

### 3. Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/Achal13jain/Fyers-data-extractor.git
   cd Fyers-data-extractor/fyers_mcx_downloader
   ```
2. Create and activate a virtual environment:
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
2. Open `.env` and fill in your credentials from Step 2:
   ```env
   FYERS_CLIENT_ID=your_client_id_here
   FYERS_SECRET_KEY=your_secret_key_here
   FYERS_REDIRECT_URI=http://127.0.0.1:5000/
   LOG_LEVEL=INFO
   ```

---

## 🔐 First-Time Authentication Flow

Because Fyers requires strict user authentication to access their API, your **first** download attempt will trigger the OAuth flow:
1. **Redirect**: A browser window will automatically open and redirect you to the Fyers Login Page.
2. **Login**: Enter your Fyers Client ID and your **4-digit PIN** as normal.
3. **The Auth Code**: After logging in, the browser will redirect you to `http://127.0.0.1:8080/` (it might look like a broken page, this is perfectly normal). **Look at the URL in your browser's address bar**. It will look something like this:
   `http://127.0.0.1:8080/?s=ok&code=YOUR_LONG_AUTH_CODE_HERE&state=...`
4. **Copy the Code**: Copy the exact value of the `code` parameter from that URL.
5. **Paste into Terminal**: Return to the terminal/command prompt where you ran the app (e.g. where `python web.py` is running). You will see it pausing and asking you to paste the auth code.
6. **Token Saved**: Press Enter. The app will securely generate an access token and save it to `token.json`! 

*Note: You only have to do this once! Future downloads will be completely automatic until the Fyers token expires.*

---

## 💻 Web App Usage (Recommended)

The easiest way to extract data is using the interactive local web server.

1. Run the FastAPI server:
   ```bash
   python web.py
   ```
2. Open your browser to `http://127.0.0.1:8000`.
3. Type in any symbol like `SILVER` or `CRUDEOIL` to search the active futures contracts dynamically.
4. Select your desired **Resolution/Timeframe** (e.g., 1 Minute, 5 Minutes, Daily).
5. Select your date ranges and click Download! The CSV will immediately compile and save to your computer.

---

## ⌨️ CLI Usage

If you prefer terminal commands for automation, the CLI is fully supported. 
*Note: On your very first run, it will open your browser to log into Fyers and generate the OAuth token. Read the console logs for instructions.*

**Download 1-min data for the default Gold symbol from Jan 2024 to today:**
```bash
python main.py --from 2024-01-01
```

**Download with a custom symbol and output file:**
```bash
python main.py --symbol MCX:GOLD25JUNFUT --from 2024-06-01 --to 2024-09-30 --output gold_jun2024.csv
```

**Supported Resolutions:**
`1`, `2`, `3`, `5`, `10`, `15`, `20`, `30`, `60`, `120`, `240`, `1D`

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. 

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information.

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
