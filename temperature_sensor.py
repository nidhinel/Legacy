import requests
import time
import random
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TemperatureReading:
    sensor_id: str
    temperature: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None


class TemperatureSensorAPI:
    """Client for a remote temperature sensor API."""

    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.timeout = timeout

    def get_reading(self, sensor_id: str) -> TemperatureReading:
        """Fetch the latest temperature reading from a sensor."""
        url = f"{self.base_url}/sensors/{sensor_id}/temperature"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        return TemperatureReading(
            sensor_id=sensor_id,
            temperature=data["temperature"],
            unit=data.get("unit", "C"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            location=data.get("location"),
        )

    def get_all_sensors(self) -> list[dict]:
        """List all available sensors."""
        url = f"{self.base_url}/sensors"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("sensors", [])

    def close(self):
        self.session.close()


def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9 / 5) + 32


def monitor(client: TemperatureSensorAPI, sensor_id: str, interval: int = 5, cycles: int = 10):
    """Poll a sensor at a fixed interval and print readings."""
    logger.info(f"Monitoring sensor '{sensor_id}' every {interval}s for {cycles} cycles...")

    for i in range(1, cycles + 1):
        try:
            reading = client.get_reading(sensor_id)
            temp_f = celsius_to_fahrenheit(reading.temperature) if reading.unit == "C" else reading.temperature
            logger.info(
                f"[{i}/{cycles}] Sensor: {reading.sensor_id} | "
                f"Temp: {reading.temperature:.2f}°{reading.unit} ({temp_f:.2f}°F) | "
                f"Time: {reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                + (f" | Location: {reading.location}" if reading.location else "")
            )
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except requests.ConnectionError:
            logger.error("Connection failed. Check network or API URL.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        if i < cycles:
            time.sleep(interval)

    logger.info("Monitoring complete.")


class MockTemperatureSensorAPI(TemperatureSensorAPI):
    """Simulates a remote sensor API for local testing."""

    def __init__(self):
        self.base_url = "mock://localhost"
        self.session = None
        self.timeout = 0
        self._base_temp = 22.0  # starting temperature in Celsius

    def get_reading(self, sensor_id: str) -> TemperatureReading:
        self._base_temp += random.uniform(-0.5, 0.5)
        return TemperatureReading(
            sensor_id=sensor_id,
            temperature=round(self._base_temp, 2),
            unit="C",
            timestamp=datetime.now(),
            location="Lab Room 1 (simulated)",
        )

    def get_all_sensors(self) -> list[dict]:
        return [{"id": "sensor_001"}, {"id": "sensor_002"}]

    def close(self):
        pass


if __name__ == "__main__":
    from config import DEMO_MODE, API_BASE_URL, API_KEY, SENSOR_ID, POLL_INTERVAL, POLL_CYCLES

    client = MockTemperatureSensorAPI() if DEMO_MODE else TemperatureSensorAPI(
        base_url=API_BASE_URL, api_key=API_KEY
    )

    if DEMO_MODE:
        logger.info("Running in DEMO MODE (simulated sensor data)")

    try:
        sensors = client.get_all_sensors()
        if sensors:
            logger.info(f"Available sensors: {[s.get('id') for s in sensors]}")

        monitor(client, SENSOR_ID, interval=POLL_INTERVAL, cycles=POLL_CYCLES)

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to API. Check your API_BASE_URL and network.")
    finally:
        client.close()
