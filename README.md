# Lyftr AI Backend Assignment

A FastAPI-based backend service for handling webhooks with HMAC signature validation, message storage, and health monitoring.

## Features

- **HMAC-SHA256 Signature Validation**: Secure webhook endpoint with signature verification
- **Idempotent Webhook Processing**: Duplicate messages are automatically handled using `message_id` as primary key
- **Message Management**: Paginated message retrieval with filtering by source and date range
- **Health Checks**: Liveness and readiness probes for container orchestration
- **Structured Logging**: JSON-formatted logs (one line per request)
- **Prometheus Metrics**: Standard metrics endpoint for monitoring
- **SQLite Database**: Lightweight database stored at `/data/app.db`

## Tech Stack

- Python 3.10
- FastAPI
- SQLite
- Docker & Docker Compose
- Prometheus client library

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py             # Pydantic models
│   ├── storage.py            # Database operations
│   ├── hmac_validation.py    # HMAC signature validation
│   ├── logging_config.py     # JSON structured logging
│   ├── metrics.py            # Prometheus metrics
│   └── routes.py             # API endpoints
├── tests/
│   ├── __init__.py
│   ├── test_webhook.py       # Webhook endpoint tests
│   ├── test_messages.py      # Messages endpoint tests
│   ├── test_health.py        # Health check tests
│   └── test_metrics.py       # Metrics endpoint tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Make (optional, for convenience commands)

### Running with Docker Compose

1. **Set the webhook secret** (optional, defaults to `change_me_in_production`):
   ```bash
   export WEBHOOK_SECRET=your_secret_key_here
   ```

2. **Build and start the service**:
   ```bash
   make build
   make up
   ```
   
   Or manually:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Check if the service is running**:
   ```bash
   curl http://localhost:8000/health/live
   ```

4. **View logs**:
   ```bash
   make logs
   ```

### Running Tests

```bash
make test
```

Or manually:
```bash
pytest tests/ -v
```

### Stopping the Service

```bash
make down
```

## API Endpoints

### POST /webhook

Receive and store webhook messages with HMAC-SHA256 signature validation.

**Headers:**
- `X-Signature`: HMAC-SHA256 signature of the raw request body
- `Content-Type`: `application/json`

**Request Body:**
```json
{
  "message_id": "unique_message_id",
  "timestamp": "2024-01-01T00:00:00Z",
  "source": "source_name",
  "raw_data": {
    "any": "data"
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Webhook received",
  "message_id": "unique_message_id",
  "duplicate": false
}
```

**Idempotency**: If a message with the same `message_id` is sent again, it returns `"duplicate": true` without creating a new record.

### GET /messages

Retrieve paginated messages with optional filtering.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 10, max: 100): Number of items per page
- `source` (string, optional): Filter by source
- `start_date` (string, optional): Filter by start date (ISO 8601)
- `end_date` (string, optional): Filter by end date (ISO 8601)

**Response (200 OK):**
```json
{
  "messages": [
    {
      "message_id": "msg_123",
      "timestamp": "2024-01-01T00:00:00Z",
      "source": "source_name",
      "raw_data": {"key": "value"},
      "created_at": "2024-01-01T00:00:00.000000"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10
}
```

### GET /health/live

Liveness probe. Always returns 200 OK.

**Response (200 OK):**
```json
{
  "status": "alive"
}
```

### GET /health/ready

Readiness probe. Returns 200 OK only if:
- Database is accessible
- `WEBHOOK_SECRET` environment variable is set

**Response (200 OK):**
```json
{
  "status": "ready"
}
```

**Response (503 Service Unavailable):**
```json
{
  "detail": "Service not ready"
}
```

### GET /metrics

Prometheus-style metrics endpoint.

**Response (200 OK):**
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/webhook",method="POST",status="201"} 10.0
...
```

## Design Decisions

### HMAC-SHA256 Signature Validation

- **Why**: Ensures webhook authenticity and prevents tampering
- **Implementation**: Uses raw request body bytes to compute signature, preventing issues with JSON parsing differences
- **Security**: Uses `hmac.compare_digest()` for constant-time comparison to prevent timing attacks

### Idempotent Webhook Processing

- **Why**: Prevents duplicate processing of the same message
- **Implementation**: Uses `message_id` as PRIMARY KEY in SQLite, leveraging database constraints
- **Behavior**: Returns success (201) for both new and duplicate messages, with `duplicate` flag indicating status

### Pagination and Filtering

- **Why**: Efficient handling of large message volumes
- **Implementation**: 
  - SQL-based pagination using LIMIT/OFFSET
  - Total count computed separately for accurate pagination metadata
  - Indexes on `timestamp` and `source` for query performance
- **Filtering**: Supports source and date range filtering with proper SQL WHERE clauses

### Health Checks

- **Liveness (`/health/live`)**: Always returns 200 - indicates the process is running
- **Readiness (`/health/ready`)**: Returns 200 only when:
  - Database connection is successful
  - `WEBHOOK_SECRET` is configured
  - This allows orchestration systems to wait until the service is fully ready

### Structured JSON Logging

- **Why**: Easy parsing by log aggregation systems (ELK, Splunk, etc.)
- **Format**: One JSON object per line with timestamp, level, message, and request metadata
- **Request Logging**: Includes method, path, status code, duration, and client IP

### Prometheus Metrics
- Exposes `/metrics` endpoint compatible with Prometheus
- Tracks HTTP request counts and durations
- Tracks webhook message ingestion statistics


### SQLite Database

- **Why**: Simple, file-based database suitable for this use case
- **Location**: `/data/app.db` (mounted as volume in Docker)
- **Schema**: Single `messages` table with indexes on `timestamp` and `source` for query performance

## Example Usage

### Sending a Webhook

```bash
# Compute HMAC signature
SECRET="your_secret_key"
BODY='{"message_id":"msg_001","timestamp":"2024-01-01T00:00:00Z","source":"test","raw_data":{"key":"value"}}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send webhook
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### Retrieving Messages

```bash
# Get first page
curl http://localhost:8000/messages

# Get page 2 with 20 items
curl http://localhost:8000/messages?page=2&page_size=20

# Filter by source
curl http://localhost:8000/messages?source=test_source

# Filter by date range
curl "http://localhost:8000/messages?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z"
```
## License

This is an assignment project for Lyftr AI.


