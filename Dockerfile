FROM python:3.11-slim

# System packages needed for building some Python packages and libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl gcc libffi-dev libssl-dev python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Copy project files
COPY . /app

# Make start script executable
RUN chmod +x /app/scripts/start.sh || true

EXPOSE 8000

# Railway provides $PORT environment variable; default to 8000
ENV PORT=8000

CMD ["/app/scripts/start.sh"]
