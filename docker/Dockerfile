FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for caching
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/ 2>/dev/null || true

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
