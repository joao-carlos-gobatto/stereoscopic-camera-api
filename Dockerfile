FROM debian:trixie-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-opencv \
    python3-numpy \
    python3-websockets \
    libglib2.0-0t64 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python3", "main.py"]
