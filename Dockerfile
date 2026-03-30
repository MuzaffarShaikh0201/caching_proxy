# Caching Proxy - Multi-stage build with Poetry

FROM python:3.14-slim as builder

ENV POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy dependency and project files
COPY pyproject.toml poetry.lock* ./
COPY scripts/ scripts/
COPY src/ src/
COPY README.md ./

# Build the package (creates dist/*.whl)
RUN poetry build

# --- Runtime stage ---
FROM python:3.14-slim

WORKDIR /app

# Install the built wheel (includes package + dependencies from metadata)
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Copy alembic config and migrations (not in wheel, needed for migrations)
COPY alembic.ini ./
COPY migrations/ migrations/

# Ensure Python can find the package
ENV PYTHONPATH="/app"

# Default command (overridden by docker-compose per service)
CMD ["api"]
