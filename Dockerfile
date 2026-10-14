# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# ── Stage 2: base ─────────────────────────────────────────────────────────────
FROM python:3.10-slim AS base
RUN groupadd -r cybersense && useradd -r -g cybersense cybersense
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/
COPY config.yaml .

# ── Stage 3: api ──────────────────────────────────────────────────────────────
FROM base AS api
USER cybersense
EXPOSE 8000
CMD ["uvicorn", "cybersense.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Stage 4: ui ───────────────────────────────────────────────────────────────
FROM base AS ui
USER cybersense
EXPOSE 8501
CMD ["streamlit", "run", "cybersense/ui/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
