.PHONY: test scan fmt lint clean dev deps

PY=python
PROJECT=test_blog_v2
ARTIFACT=blog_code_v1

# Development
dev:
	@echo "🚀 Starting VISTA V-Loop development environment"
	@echo "Available commands:"
	@echo "  make test    - Run all tests"
	@echo "  make scan    - Run security scan"
	@echo "  make fmt     - Format code"
	@echo "  make lint    - Run linters"
	@echo "  make deps    - Install dependencies"
	@echo "  make clean   - Clean generated files"

# Dependencies
deps:
	pip install -U pip
	pip install bandit ruff pytest
	pip install -e .

# Formatting
fmt:
	ruff check --fix || true
	ruff format .

# Linting
lint:
	@echo "🔍 Running linters..."
	ruff check .
	bandit -q -r vista/ -f json || true

# Testing
test:
	@echo "🧪 Running tests..."
	$(PY) test_v2_migration.py
	$(PY) verify_production_readiness.py

# Security scan
scan:
	@echo "🔒 Running security scan..."
	$(PY) -m vista.cli scan --project $(PROJECT) --code-artifacts $(ARTIFACT) --json

# Production readiness check
prod-check: test lint scan
	@echo "✅ All production checks passed!"

# Clean generated files
clean:
	rm -rf ./artifacts/ ./logs/ .pytest_cache/ .ruff_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -delete

# Demo project setup
demo:
	@echo "🎭 Setting up demo project..."
	$(PY) -c "from vista.memory.projects import ProjectStore; ProjectStore().create_project('demo_blog', 'Demo Blog', 'Example blog application')"
	@echo "✅ Demo project created: demo_blog"

# List runners
runners:
	$(PY) -m vista.cli runners

# List projects
projects:
	$(PY) -m vista.cli projects

# Full CI pipeline
ci: deps test lint
	@echo "✅ CI pipeline completed successfully"

help:
	@make dev
