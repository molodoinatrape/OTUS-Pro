.PHONY: run lint format test coverage

run:
	poetry run python log_analyzer.py
lint:
	poetry run isort --check-only log_analyzer.py tests
	poetry run black --check log_analyzer.py tests
	poetry run flake8 log_analyzer.py tests
	poetry run mypy log_analyzer.py
format:
	poetry run isort log_analyzer.py tests
	poetry run black log_analyzer.py tests
test:
	poetry run python -m pytest tests -q
coverage:
	poetry run python -m pytest tests --cov=log_analyzer --cov-report=term-missing