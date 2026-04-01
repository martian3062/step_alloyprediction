FROM python:3.11-slim

# System dependencies for OCP (OpenCascade) and GMSH
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglu1-mesa \
    libgomp1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
ENV FLASK_APP=backend.app:app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "300", "--preload", "backend.app:app"]
