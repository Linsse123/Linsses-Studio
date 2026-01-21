FROM python:3.9-slim

# Instalación de Poppler (indispensable)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Instalación de librerías sin guardar caché para ahorrar espacio
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]