import time

from prometheus_client import CollectorRegistry, Counter, disable_created_metrics

disable_created_metrics()
registry = CollectorRegistry()
requests_processed = Counter(
    "app_requests_processed_total",
    "Sound classification requests processed on this device",
    registry=registry,
)


def run_metric_test() -> None:
    while True:
        time.sleep(5)
        requests_processed.inc()
