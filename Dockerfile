FROM python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY ./requirements.txt /app

RUN uv pip install --system -r requirements.txt

COPY . /app

ENV PORT=4000
EXPOSE $PORT

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
