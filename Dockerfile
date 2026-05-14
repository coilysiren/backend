FROM python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY . /app
RUN uv sync --frozen --no-dev

ENV PORT=4000
EXPOSE $PORT

CMD ["sh", "-c", ".venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
