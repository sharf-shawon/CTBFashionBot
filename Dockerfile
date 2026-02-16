FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev libpq-dev

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN uv pip install --system --no-cache -e .

RUN adduser -D appuser && \
    mkdir -p /app/storage/data /app/storage/logs && \
    chown -R appuser:appuser /app/storage

USER appuser

CMD ["python", "src/main.py"]
