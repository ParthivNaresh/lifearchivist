FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

# Copy application code
COPY lifearchivist/ ./lifearchivist/

# Create data directories
RUN mkdir -p /app/data /app/vault

# Set environment variables
ENV PYTHONPATH=/app
ENV LIFEARCH_HOME=/app/data

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "lifearchivist.server.mcp_server"]