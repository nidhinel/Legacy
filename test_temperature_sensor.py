import threading
import unittest
from datetime import datetime, timezone
from temperature_sensor import (
    TemperatureReading,
    SensorAPIBase,
    SensorError,
    SensorConnectionError,
    SensorNotFoundError,
    MockTemperatureSensorAPI,
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    to_celsius,
    monitor,
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


class TestFahrenheitToCelsius(unittest.TestCase):
    def test_freezing(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(32), 0.0)

    def test_boiling(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(212), 100.0)

    def test_body_temp(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(98.6), 37.0, places=1)

    def test_negative(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(-40), -40.0)

    def test_roundtrip(self):
        for temp in [-10, 0, 22, 37, 100]:
            self.assertAlmostEqual(fahrenheit_to_celsius(celsius_to_fahrenheit(temp)), temp, places=6)


class TestToCelsius(unittest.TestCase):
    def _reading(self, temp, unit):
        return TemperatureReading(sensor_id="s1", temperature=temp, unit=unit, timestamp=datetime.now())

    def test_celsius_passthrough(self):
        self.assertAlmostEqual(to_celsius(self._reading(22.0, "C")), 22.0)

    def test_fahrenheit_converted(self):
        self.assertAlmostEqual(to_celsius(self._reading(32.0, "F")), 0.0)

    def test_body_temp_f(self):
        self.assertAlmostEqual(to_celsius(self._reading(98.6, "F")), 37.0, places=1)


class TestMockTemperatureBounds(unittest.TestCase):
    def test_temperature_stays_in_bounds(self):
        api = MockTemperatureSensorAPI()
        for _ in range(500):
            reading = api.get_reading("sensor_001")
            self.assertGreaterEqual(reading.temperature, 15.0)
            self.assertLessEqual(reading.temperature, 35.0)


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

    def test_invalid_unit_raises(self):
        with self.assertRaises(ValueError):
            TemperatureReading(sensor_id="s1", temperature=20.0, unit="X", timestamp=datetime.now())

    def test_fahrenheit_unit_accepted(self):
        r = TemperatureReading(sensor_id="s1", temperature=68.0, unit="F", timestamp=datetime.now())
        self.assertEqual(r.unit, "F")

    def test_infinite_temperature_raises(self):
        with self.assertRaises(ValueError):
            TemperatureReading(sensor_id="s1", temperature=float("inf"), unit="C", timestamp=datetime.now())

    def test_nan_temperature_raises(self):
        with self.assertRaises(ValueError):
            TemperatureReading(sensor_id="s1", temperature=float("nan"), unit="C", timestamp=datetime.now())

    def test_empty_sensor_id_raises(self):
        with self.assertRaises(ValueError):
            TemperatureReading(sensor_id="", temperature=20.0, unit="C", timestamp=datetime.now())


class TestMockTemperatureSensorAPI(unittest.TestCase):
    def setUp(self):
        self.api = MockTemperatureSensorAPI()

    def test_is_sensor_api_base(self):
        self.assertIsInstance(self.api, SensorAPIBase)

    def test_get_reading_returns_temperature_reading(self):
        reading = self.api.get_reading("sensor_001")
        self.assertIsInstance(reading, TemperatureReading)

    def test_get_reading_sensor_id_matches(self):
        reading = self.api.get_reading("sensor_001")
        self.assertEqual(reading.sensor_id, "sensor_001")

    def test_get_reading_unknown_sensor_raises(self):
        with self.assertRaises(SensorNotFoundError) as ctx:
            self.api.get_reading("sensor_999")
        self.assertEqual(ctx.exception.sensor_id, "sensor_999")

    def test_sensor_001_location(self):
        reading = self.api.get_reading("sensor_001")
        self.assertIn("Room 1", reading.location)

    def test_sensor_002_location(self):
        reading = self.api.get_reading("sensor_002")
        self.assertIn("Room 2", reading.location)

    def test_get_reading_unit_is_celsius(self):
        reading = self.api.get_reading("sensor_001")
        self.assertEqual(reading.unit, "C")

    def test_get_reading_temperature_fluctuates(self):
        readings = [self.api.get_reading("sensor_001").temperature for _ in range(20)]
        self.assertGreater(max(readings) - min(readings), 0)

    def test_get_reading_timestamp_is_recent(self):
        before = datetime.now(timezone.utc)
        reading = self.api.get_reading("sensor_001")
        after = datetime.now(timezone.utc)
        self.assertGreaterEqual(reading.timestamp, before)
        self.assertLessEqual(reading.timestamp, after)

    def test_get_all_sensors_returns_list(self):
        sensors = self.api.get_all_sensors()
        self.assertIsInstance(sensors, list)
        self.assertTrue(len(sensors) > 0)

    def test_get_all_sensors_includes_location(self):
        for sensor in self.api.get_all_sensors():
            self.assertIn("id", sensor)
            self.assertIn("location", sensor)
            self.assertIsNotNone(sensor["location"])

    def test_close_does_not_raise(self):
        self.api.close()

    def test_context_manager(self):
        with MockTemperatureSensorAPI() as api:
            reading = api.get_reading("sensor_001")
            self.assertIsInstance(reading, TemperatureReading)


class TestSensorExceptions(unittest.TestCase):
    def test_sensor_not_found_is_sensor_error(self):
        self.assertTrue(issubclass(SensorNotFoundError, SensorError))

    def test_sensor_connection_error_is_sensor_error(self):
        self.assertTrue(issubclass(SensorConnectionError, SensorError))

    def test_sensor_error_is_exception(self):
        self.assertTrue(issubclass(SensorError, Exception))

    def test_sensor_not_found_carries_message(self):
        exc = SensorNotFoundError("sensor_001")
        self.assertIn("sensor_001", str(exc))


class TestMonitor(unittest.TestCase):
    def test_returns_dict_with_readings_and_errors(self):
        api = MockTemperatureSensorAPI()
        stats = monitor(api, "sensor_001", interval=0, cycles=3)
        self.assertEqual(stats["readings"], 3)
        self.assertEqual(stats["errors"], 0)

    def test_errors_counted_on_sensor_error(self):
        class _ErrorClient(SensorAPIBase):
            def get_reading(self, sensor_id):
                raise SensorError("boom")
            def get_all_sensors(self):
                return []
            def close(self):
                pass

        stats = monitor(_ErrorClient(), "sensor_001", interval=0, cycles=4)
        self.assertEqual(stats["readings"], 0)
        self.assertEqual(stats["errors"], 4)

    def test_aborts_on_sensor_not_found(self):
        api = MockTemperatureSensorAPI()
        stats = monitor(api, "sensor_999", interval=0, cycles=5)
        self.assertEqual(stats["readings"], 0)
        self.assertEqual(stats["errors"], 0)


class TestMonitorStopEvent(unittest.TestCase):
    def test_stop_event_halts_loop_early(self):
        api = MockTemperatureSensorAPI()
        stop = threading.Event()
        stop.set()
        stats = monitor(api, "sensor_001", interval=0, cycles=10, stop_event=stop)
        self.assertEqual(stats["readings"], 0)

    def test_stop_event_mid_run(self):
        api = MockTemperatureSensorAPI()
        stop = threading.Event()
        call_count = 0
        original = api.get_reading

        def counting_get(sid):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                stop.set()
            return original(sid)

        api.get_reading = counting_get
        stats = monitor(api, "sensor_001", interval=0, cycles=10, stop_event=stop)
        self.assertLess(stats["readings"], 10)


class TestMockPerSensorState(unittest.TestCase):
    def test_two_sensors_have_independent_walks(self):
        api = MockTemperatureSensorAPI()
        for _ in range(50):
            api.get_reading("sensor_001")
        for _ in range(50):
            api.get_reading("sensor_002")
        temp_a = api.get_reading("sensor_001").temperature
        temp_b = api.get_reading("sensor_002").temperature
        self.assertNotEqual(temp_a, temp_b)


if __name__ == "__main__":
    unittest.main()
