.PHONY: lint
lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run ty check

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix

.PHONY: test
test:
	uv run pytest tests

.PHONY: test-cov
test-cov:
	uv run pytest tests \
		--cov src \
		--cov-branch \
		--junitxml pytest.xml \
		--cov-report term-missing:skip-covered | tee pytest-coverage.txt
