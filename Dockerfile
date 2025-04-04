FROM python:3.11

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENV PORT=4000

CMD ["uvicorn", "src.main:app", "--host=0.0.0.0", "--port=$PORT"]
