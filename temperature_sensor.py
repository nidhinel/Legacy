import requests
import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SensorError(Exception):
    """Raised when a sensor operation fails."""

class SensorNotFoundError(SensorError):
    """Raised when the requested sensor does not exist."""


@dataclass
class TemperatureReading:
    sensor_id: str
    temperature: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None

    def __post_init__(self):
        if self.unit not in ("C", "F"):
            raise ValueError(f"unit must be 'C' or 'F', got {self.unit!r}")


class SensorAPIBase(ABC):
    """Abstract base for temperature sensor API clients."""

    @abstractmethod
    def get_reading(self, sensor_id: str) -> TemperatureReading: ...

    @abstractmethod
    def get_all_sensors(self) -> list[dict]: ...

    @abstractmethod
    def close(self): ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TemperatureSensorAPI(SensorAPIBase):
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
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise SensorNotFoundError(sensor_id) from e
            raise SensorError(str(e)) from e
        except requests.ConnectionError as e:
            raise SensorError("Connection failed. Check network or API URL.") from e
        except requests.RequestException as e:
            raise SensorError(str(e)) from e

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
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise SensorError(str(e)) from e
        return response.json().get("sensors", [])

    def close(self):
        self.session.close()


def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9 / 5) + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    return (fahrenheit - 32) * 5 / 9


def to_celsius(reading: TemperatureReading) -> float:
    """Return reading temperature normalised to Celsius."""
    if reading.unit == "F":
        return fahrenheit_to_celsius(reading.temperature)
    return reading.temperature


def monitor(client: SensorAPIBase, sensor_id: str, interval: int = 5, cycles: int = 10):
    """Poll a sensor at a fixed interval and print readings."""
    logger.info(f"Monitoring sensor '{sensor_id}' every {interval}s for {cycles} cycles...")

    for i in range(1, cycles + 1):
        try:
            reading = client.get_reading(sensor_id)
            temp_c = to_celsius(reading)
            temp_f = celsius_to_fahrenheit(temp_c)
            logger.info(
                f"[{i}/{cycles}] Sensor: {reading.sensor_id} | "
                f"Temp: {temp_c:.2f}°C ({temp_f:.2f}°F) | "
                f"Time: {reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                + (f" | Location: {reading.location}" if reading.location else "")
            )
        except SensorNotFoundError:
            logger.error(f"Sensor '{sensor_id}' not found. Aborting.")
            break
        except SensorError as e:
            logger.error(f"Sensor error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        if i < cycles:
            time.sleep(interval)

    logger.info("Monitoring complete.")


class MockTemperatureSensorAPI(SensorAPIBase):
    """Simulates a remote sensor API for local testing."""

    def __init__(self):
        self._temps: dict[str, float] = {}

    def get_reading(self, sensor_id: str) -> TemperatureReading:
        temp = self._temps.get(sensor_id, 22.0) + random.uniform(-0.5, 0.5)
        self._temps[sensor_id] = max(15.0, min(35.0, temp))
        return TemperatureReading(
            sensor_id=sensor_id,
            temperature=round(self._temps[sensor_id], 2),
            unit="C",
            timestamp=datetime.now(),
            location="Lab Room 1 (simulated)",
        )

    def get_all_sensors(self) -> list[dict]:
        return [{"id": "sensor_001"}, {"id": "sensor_002"}]

    def close(self):
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from config import DEMO_MODE, API_BASE_URL, API_KEY, SENSOR_ID, POLL_INTERVAL, POLL_CYCLES

    client = MockTemperatureSensorAPI() if DEMO_MODE else TemperatureSensorAPI(
        base_url=API_BASE_URL, api_key=API_KEY
    )

    if DEMO_MODE:
        logger.info("Running in DEMO MODE (simulated sensor data)")

    with client:
        sensors = client.get_all_sensors()
        if sensors:
            logger.info(f"Available sensors: {[s.get('id') for s in sensors]}")
        monitor(client, SENSOR_ID, interval=POLL_INTERVAL, cycles=POLL_CYCLES)
