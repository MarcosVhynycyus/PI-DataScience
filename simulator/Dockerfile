FROM python:3.10-slim

WORKDIR /app

# Instala dependências de sistema para compilar o psycopg2 se necessário
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000