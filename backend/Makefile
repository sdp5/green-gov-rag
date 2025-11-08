
.PHONY: help clean dist test devel mypy lint fix format deploy-aws ingest run migrate migrate-rollback migrate-history

help:
	@echo "Available commands:"
	@echo ""
	@echo "    clean: clears build, pyc and test files"
	@echo "    dist: build the package"
	@echo "    test: run pytest on all unit tests"
	@echo "    mypy: run mypy on the library"
	@echo "    lint: run pylint on the library"
	@echo "    fix: run fixers for consistent code formatting"
	@echo "    format: executes mypy, lint and fix commands"
	@echo "    migrate: run database migrations (alembic upgrade head)"
	@echo "    migrate-rollback: rollback last migration (alembic downgrade -1)"
	@echo "    migrate-history: show migration history (alembic history)"

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -f .coverage
	rm -fr htmlcov/

clean: clean-build clean-pyc clean-test

dist:
	python3 -m build

test:
	pytest --cov-report term --cov=green_gov_rag tests

dev-env:
	pip install -e .[dev]

setup:
	virtualenv --python=python3.12 .venv && source .venv/bin/activate

devel: setup dev-env

mypy:
	mypy --exclude conftest.py --check-untyped-defs green_gov_rag tests

lint-ruff:
	ruff check green_gov_rag tests

lint-pylint:
	pylint green_gov_rag tests

lint-pylint-ci: lint-ruff
	pylint green_gov_rag tests --disable fixme

lint: lint-ruff lint-pylint

lint-ci: lint-ruff lint-pylint-ci

import-fix:
	ruff check --select I --fix .

format: import-fix
	ruff format green_gov_rag tests

deploy-aws:
	cdk deploy

ingest:
	python scripts/ingest_docs.py

run:
	uvicorn green_gov_rag.api.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migrate-rollback:
	alembic downgrade -1

migrate-history:
	alembic history --verbose
