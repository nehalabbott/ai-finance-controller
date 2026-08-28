# Use lightweight official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements or install packages directly
RUN pip install --no-cache-dir pandas fastapi uvicorn google-genai pydantic

# Copy project files into the container
COPY . /app/

# Expose port for FastAPI webhook receiver
EXPOSE 8000

# Default command runs the automated pipeline or can be overridden
CMD ["python", "main.py"]