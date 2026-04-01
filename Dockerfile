FROM python:3.11-slim

# Install minimal system dependencies for GMSH geometry engine
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglu1-mesa \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for production performance and RAM stability
ENV PORT=5000
ENV FLASK_APP=backend.app:app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2

# Expose port
EXPOSE 5000

# Start command with reduced concurrency for 512MB RAM
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "300", "--preload", "backend.app:app"]
