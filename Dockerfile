FROM python:3.10-slim

WORKDIR /app
ENV WEBHOOK_SECRET=testsecret
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/


# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

