FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN addgroup --gid 1000 appuser && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos "" appuser

# Install dependencies first (better layer caching)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config config
COPY core core
COPY main.py main.py
COPY test_fetch.py test_fetch.py

# Set ownership
RUN chown -R 1000:1000 /app

USER appuser

# Default command: run infrastructure test
CMD ["python", "main.py"]
