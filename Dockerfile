FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FORWARDED_ALLOW_IPS=""

WORKDIR /app

# Debian fornece ffprobe no pacote ffmpeg; sem recomendações nem ferramentas no host.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 signage \
    && useradd --uid 10001 --gid signage --no-create-home signage

COPY app/ ./app/
COPY tests/ ./tests/

RUN mkdir -p /app/data /app/media && chown signage:signage /app/data /app/media

USER signage
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
