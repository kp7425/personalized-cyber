FROM python:3.11-slim

# Install system dependencies (needed for some python packages like psycopg2)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY database/ database/

# Set python path so src modules are found
ENV PYTHONPATH=/app

# Default command (overridden by K8s args)
CMD ["python", "src/lms/app.py"]
