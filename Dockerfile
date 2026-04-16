# Use official Python runtime as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (we'll install from pixi.toml dependencies)
COPY pixi.toml pyproject.toml* ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    fastapi>=0.135.3 \
    uvicorn>=0.44.0 \
    streamlit>=1.56.0 \
    plotly>=6.7.0 \
    scikit-learn>=1.8.0 \
    pandas>=3.0.2 \
    numpy>=2.4.4

# Copy application code
COPY app ./app
COPY streamlit_app ./streamlit_app
COPY data ./data

# Create data directory if it doesn't exist
RUN mkdir -p /app/data

# Expose ports
EXPOSE 8000 8501

# Default command runs the API (can be overridden for dashboard)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
