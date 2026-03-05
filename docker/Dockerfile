FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY .env .env

# Create required directories
RUN mkdir -p vectorstore/chroma_db documents/uploads logs evaluation/results

# Expose ports
EXPOSE 8000 8501

# Default command (overridden by docker-compose)
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
