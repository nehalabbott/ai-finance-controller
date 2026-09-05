# Use lightweight official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Replaced google-genai with groq and added streamlit for the dashboard
RUN pip install --no-cache-dir pandas fastapi uvicorn groq pydantic streamlit

# Copy project files into the container
COPY . /app/

# Expose ports for FastAPI webhook receiver and Streamlit dashboard
EXPOSE 8000
EXPOSE 8501

# Default command runs the automated pipeline or can be overridden
CMD ["python", "main.py"]