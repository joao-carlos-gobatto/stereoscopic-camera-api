FROM python:3.12-slim

WORKDIR /app 

# Evita cache e melhora logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Se tiver dependências 
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY . .
CMD ["python", "main.py"]
