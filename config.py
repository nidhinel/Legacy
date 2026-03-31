import os

DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.example.com/v1")
API_KEY = os.environ.get("API_KEY", "")
SENSOR_ID = os.environ.get("SENSOR_ID", "sensor_001")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "2"))
POLL_CYCLES = int(os.environ.get("POLL_CYCLES", "8"))
