FROM python:3.10-slim

WORKDIR /app

# Instalăm bibliotecile de sistem necesare pentru procesarea imaginilor
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalăm dependențele Python direct pentru a păstra imaginea mică
RUN pip install --no-cache-dir fastapi uvicorn requests Pillow imagehash

COPY main.py .

# Expunem portul 80 pentru Bunny ML
EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]