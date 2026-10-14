.PHONY: setup install download ingest run ui test lint eval up down clean

# ── Setup ─────────────────────────────────────────────────────────────────────
setup:
	pip install -e ".[dev]"
	pre-commit install
	cp -n .env.example .env || true
	mkdir -p data/raw data/processed docs eval/reports db

install:
	pip install -e .

# ── Data ──────────────────────────────────────────────────────────────────────
download:
	py scripts/download_sources.py

ingest:
	py scripts/ingest.py --source all

# ── Dev servers ───────────────────────────────────────────────────────────────
run:
	uvicorn cybersense.api.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run src/cybersense/ui/app.py --server.port 8501

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/ scripts/
	black --check src/ tests/ scripts/
	mypy src/

format:
	ruff check --fix src/ tests/ scripts/
	black src/ tests/ scripts/

test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

# ── Evaluation ────────────────────────────────────────────────────────────────
eval:
	py scripts/run_eval.py

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up --build -d

down:
	docker compose down

# ── Housekeeping ──────────────────────────────────────────────────────────────
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
