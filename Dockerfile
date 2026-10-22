# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first (for better caching)
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Expose port 
EXPOSE 8000

# Set environment variables to avoid prompts during installation
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create logs directory
RUN mkdir -p ./logs

# Default command  
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]