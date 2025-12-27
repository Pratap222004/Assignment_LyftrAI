from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY

# Create a custom registry
metrics_registry = CollectorRegistry()

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=metrics_registry
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=metrics_registry
)

webhook_messages_total = Counter(
    "webhook_messages_total",
    "Total number of webhook messages received",
    ["source", "status"],
    registry=metrics_registry
)

messages_in_db = Gauge(
    "messages_in_db",
    "Total number of messages in database",
    registry=metrics_registry
)


def setup_metrics():
    """Setup metrics (called on app startup)"""
    pass


def get_metrics_registry():
    """Get the metrics registry"""
    return metrics_registry

