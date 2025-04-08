FROM python:3.11

WORKDIR /app
COPY ./requirements.txt /app

RUN pip install -r requirements.txt

COPY . /app

ENV PORT=4000
EXPOSE $PORT

CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT"]
