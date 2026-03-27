.PHONY: install run format test clean

# Install dependencies in current environment
install:
	pip install -r requirements.txt

# Run the web server UI
run:
	python web.py

# Format the code (Requires black; pip install black)
format:
	black .

# Run tests (Requires pytest; pip install pytest)
test:
	pytest

# Clean up pycache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
