FROM python:3.11-slim

# 1. Instalar dependencias del sistema necesarias para OpenCV y PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiar el resto de la aplicación
COPY . .

# 4. Exponer puerto y comando de inicio
EXPOSE 5000
CMD ["python", "app.py"]