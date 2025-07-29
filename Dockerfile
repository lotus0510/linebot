FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

ENV PORT 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
