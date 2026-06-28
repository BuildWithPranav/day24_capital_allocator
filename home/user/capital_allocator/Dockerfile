FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install -U pip && pip install .

COPY config ./config
COPY src ./src
ENV PYTHONPATH=/app/src

EXPOSE 8080
CMD ["python", "-m", "capital_allocator.main"]
