# Contributing to Fyers MCX Data Extractor

First off, thank you for considering contributing to the Fyers MCX Data Extractor! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

## Where to Start?

1. **Issues:** Check the [Issues](https://github.com/Achal13jain/Fyers-data-extractor/issues) tab for any open bugs or feature requests. 
2. **Discussions:** Feel free to open a discussion if you have an idea for a massive architectural change or new feature.

## Development Setup

1. **Fork the Repository** on GitHub.
2. **Clone your branch** to your local machine:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Fyers-data-extractor.git
   ```
3. **Set up a Virtual Environment**:
   ```bash
   cd Fyers-data-extractor/fyers_mcx_downloader
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Mac/Linux: source venv/bin/activate
   ```
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Configure environment variables** in a `.env` file based on `.env.example`.

## Making Changes

- **Create a Branch**: Always create a new branch for your work (e.g., `feat/add-new-api-endpoint` or `fix/button-styling`).
- **Code Standards**: 
  - Follow PEP 8 guidelines for Python code.
  - Make sure all functions are properly typed using Python type hints (`-> str:`).
  - Write descriptive, informative commit messages.
- **Testing**: Test your changes thoroughly by running both the Web App (`python web.py`) and the CLI (`python main.py`).

## Pull Requests

1. Commit your changes locally.
2. Push your branch to your forked repository.
3. Open a Pull Request against the `main` branch of this repository.
4. Describe your changes in detail, including screenshots for any Web UI modifications.

Thank you for contributing!
