# Use Python 3.12 slim image
FROM python:3.12-slim

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set environment variables for uv and Flet
ENV UV_SYSTEM_PYTHON=1
ENV UV_COMPILE_BYTECODE=1
ENV FLET_SERVER_PORT=8000
ENV FLET_SERVER_ADDRESS=0.0.0.0

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies without the project (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Copy application source code
COPY src/ ./src/

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Expose port for Flet web app
EXPOSE 8000

# Run the Flet application
CMD ["uv", "run", "python", "-m", "flet", "run", "src/main.py", "--web", "--port", "8000"]