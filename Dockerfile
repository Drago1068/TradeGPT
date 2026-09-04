FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip pytest
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0"]
