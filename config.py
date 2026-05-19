import os
import warnings

DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.com/v1")
API_KEY = os.environ.get("API_KEY", "")
SENSOR_ID = os.environ.get("SENSOR_ID", "sensor_001")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "2"))
POLL_CYCLES = int(os.environ.get("POLL_CYCLES", "8"))

if not (1 <= POLL_INTERVAL <= 3600):
    raise ValueError(f"POLL_INTERVAL must be between 1 and 3600, got {POLL_INTERVAL}")

if not (1 <= POLL_CYCLES <= 10000):
    raise ValueError(f"POLL_CYCLES must be between 1 and 10000, got {POLL_CYCLES}")

if not DEMO_MODE and not API_KEY:
    warnings.warn(
        "DEMO_MODE is false but API_KEY is not set. "
        "Set the API_KEY environment variable before connecting to a real sensor.",
        RuntimeWarning,
        stacklevel=1,
    )
