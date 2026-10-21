FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 INNINGS_HOME=/app PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
EXPOSE 8453
# First start downloads the data and builds the models. Later starts reuse data/.
CMD ["sh", "-c", "[ -f data/innings.duckdb ] || innings all; exec innings serve --host 0.0.0.0"]
