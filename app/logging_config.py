import json
import logging
import time
from datetime import datetime
from fastapi import Request, Response

# Configure JSON logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging():
    """Setup JSON structured logging"""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def log_request(request: Request, response: Response):
    """Log HTTP request in JSON format"""
    logger = logging.getLogger("http")
    
    # Calculate duration
    if hasattr(request.state, "start_time"):
        duration_ms = (time.time() - request.state.start_time) * 1000
    else:
        duration_ms = 0
    
    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": request.client.host if request.client else None,
    }
    
    logger.info("HTTP request", extra={"extra_fields": log_data})

