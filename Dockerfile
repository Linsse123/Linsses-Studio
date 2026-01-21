# Usamos Python ligero
FROM python:3.9-slim

# INSTALAR POPPLER (Vital para leer PDFs en la nube)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Configurar carpeta de trabajo
WORKDIR /app

# Copiar archivos
COPY . .

# Instalar librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Abrir el puerto 5000
EXPOSE 5000

# Ejecutar la app
CMD ["python", "app.py"]