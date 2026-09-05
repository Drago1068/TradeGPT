FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir 'pytest>=8,<9' 'httpx>=0.28,<1'

ENV PYTHONPATH=/app/src
EXPOSE 8080

CMD ["uvicorn", "tradegpt.app:app", "--host", "0.0.0.0", "--port", "8080"]
