FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY src/python/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (lean microservices)
COPY src/ src/
COPY start.sh start.sh

# Convert line endings and make executable
RUN dos2unix start.sh && chmod +x start.sh

EXPOSE 8005

ENV HOST=0.0.0.0
ENV PORT=8005
ENV PYTHONPATH=/app/src/python:/app/src/python/agents:/app/src/python/mcp_server/customer_sales:/app/src/python/workshop

CMD ["/app/start.sh"]
