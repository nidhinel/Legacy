import unittest
from fastapi.testclient import TestClient
from temperature_sensor import MockTemperatureSensorAPI
from api_server import app, get_client


def _mock_client():
    return MockTemperatureSensorAPI()


app.dependency_overrides[get_client] = _mock_client


class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_200(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)

    def test_health_has_status_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.json()["status"], "ok")

    def test_health_has_mode(self):
        r = self.client.get("/health")
        self.assertIn(r.json()["mode"], ("demo", "live"))


class TestListSensors(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_returns_200(self):
        r = self.client.get("/sensors")
        self.assertEqual(r.status_code, 200)

    def test_response_has_sensors_key(self):
        r = self.client.get("/sensors")
        self.assertIn("sensors", r.json())

    def test_sensors_is_nonempty_list(self):
        r = self.client.get("/sensors")
        sensors = r.json()["sensors"]
        self.assertIsInstance(sensors, list)
        self.assertGreater(len(sensors), 0)


class TestGetTemperature(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_returns_200(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        self.assertEqual(r.status_code, 200)

    def test_response_fields_present(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        body = r.json()
        for field in ("sensor_id", "temperature_c", "temperature_f", "unit", "timestamp"):
            self.assertIn(field, body)

    def test_sensor_id_matches(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        self.assertEqual(r.json()["sensor_id"], "sensor_001")

    def test_unknown_sensor_returns_404(self):
        r = self.client.get("/sensors/sensor_999/temperature")
        self.assertEqual(r.status_code, 404)

    def test_invalid_sensor_id_returns_422(self):
        r = self.client.get("/sensors/bad id!/temperature")
        self.assertEqual(r.status_code, 422)

    def test_temperature_f_is_conversion_of_c(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        body = r.json()
        expected_f = round((body["temperature_c"] * 9 / 5) + 32, 2)
        self.assertAlmostEqual(body["temperature_f"], expected_f, places=1)

    def test_temperature_c_in_expected_range(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        temp_c = r.json()["temperature_c"]
        self.assertGreaterEqual(temp_c, 15.0)
        self.assertLessEqual(temp_c, 35.0)

    def test_unit_is_celsius(self):
        r = self.client.get("/sensors/sensor_001/temperature")
        self.assertEqual(r.json()["unit"], "C")


if __name__ == "__main__":
    unittest.main()
