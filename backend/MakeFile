.PHONY: lint
lint:
	poetry run isort . --check-only
	poetry run black . --check
	poetry run mypy .

.PHONY: format
format:
	poetry run isort .
	poetry run black .

.PHONY: test
test:
	poetry run pytest tests

.PHONY: test-cov
test-cov:
	poetry run pytest tests \
		--cov src \
		--cov-branch \
		--junitxml pytest.xml \
		--cov-report term-missing:skip-covered | tee pytest-coverage.txt