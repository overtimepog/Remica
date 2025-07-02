.PHONY: help install setup test run clean lint format init-db

help:
	@echo "Real Estate Market Insights Chat Agent - Available Commands"
	@echo "=========================================================="
	@echo "make install    - Install dependencies"
	@echo "make setup      - Run complete setup (venv + dependencies + config)"
	@echo "make test       - Run all tests"
	@echo "make run        - Run the application"
	@echo "make clean      - Clean up cache and temporary files"
	@echo "make lint       - Run code linters"
	@echo "make format     - Format code with black"
	@echo "make init-db    - Initialize database tables"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

setup:
	@bash setup.sh

test:
	pytest -v

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing

run:
	python main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/ main.py

init-db:
	python main.py --init-db