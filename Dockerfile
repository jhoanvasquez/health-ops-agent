FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000

# Default command (used by the API on Render, which doesn't override it): apply
# migrations, then serve. Exec-form `sh -c` keeps the shell inside the image, so the
# `&&` is honored regardless of how the platform launches the container. $PORT is set
# by Render; locally compose overrides this command entirely (see docker-compose.yml).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
