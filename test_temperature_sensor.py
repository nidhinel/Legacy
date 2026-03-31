import unittest
from datetime import datetime
from temperature_sensor import (
    TemperatureReading,
    MockTemperatureSensorAPI,
    celsius_to_fahrenheit,
)


class TestCelsiusToFahrenheit(unittest.TestCase):
    def test_freezing(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(0), 32.0)

    def test_boiling(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(100), 212.0)

    def test_body_temp(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(37), 98.6, places=1)

    def test_negative(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(-40), -40.0)


class TestTemperatureReading(unittest.TestCase):
    def test_fields(self):
        ts = datetime(2026, 1, 1, 12, 0, 0)
        r = TemperatureReading(
            sensor_id="s1",
            temperature=22.5,
            unit="C",
            timestamp=ts,
            location="Lab",
        )
        self.assertEqual(r.sensor_id, "s1")
        self.assertEqual(r.temperature, 22.5)
        self.assertEqual(r.unit, "C")
        self.assertEqual(r.timestamp, ts)
        self.assertEqual(r.location, "Lab")

    def test_optional_location_defaults_to_none(self):
        r = TemperatureReading(
            sensor_id="s1", temperature=20.0, unit="C", timestamp=datetime.now()
        )
        self.assertIsNone(r.location)


class TestMockTemperatureSensorAPI(unittest.TestCase):
    def setUp(self):
        self.api = MockTemperatureSensorAPI()

    def test_get_reading_returns_temperature_reading(self):
        reading = self.api.get_reading("sensor_001")
        self.assertIsInstance(reading, TemperatureReading)

    def test_get_reading_sensor_id_matches(self):
        reading = self.api.get_reading("sensor_007")
        self.assertEqual(reading.sensor_id, "sensor_007")

    def test_get_reading_unit_is_celsius(self):
        reading = self.api.get_reading("sensor_001")
        self.assertEqual(reading.unit, "C")

    def test_get_reading_temperature_fluctuates(self):
        readings = [self.api.get_reading("sensor_001").temperature for _ in range(20)]
        self.assertGreater(max(readings) - min(readings), 0)

    def test_get_reading_timestamp_is_recent(self):
        before = datetime.now()
        reading = self.api.get_reading("sensor_001")
        after = datetime.now()
        self.assertGreaterEqual(reading.timestamp, before)
        self.assertLessEqual(reading.timestamp, after)

    def test_get_all_sensors_returns_list(self):
        sensors = self.api.get_all_sensors()
        self.assertIsInstance(sensors, list)
        self.assertTrue(len(sensors) > 0)

    def test_close_does_not_raise(self):
        self.api.close()


if __name__ == "__main__":
    unittest.main()
