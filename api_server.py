from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from config import DEMO_MODE, API_BASE_URL, API_KEY, SENSOR_ID
from temperature_sensor import (
    MockTemperatureSensorAPI,
    TemperatureSensorAPI,
    celsius_to_fahrenheit,
    to_celsius,
)

app = FastAPI(title="Temperature Sensor API", version="1.0.0")

_client = MockTemperatureSensorAPI() if DEMO_MODE else TemperatureSensorAPI(API_BASE_URL, API_KEY)


class ReadingResponse(BaseModel):
    sensor_id: str
    temperature_c: float
    temperature_f: float
    unit: str
    location: Optional[str]
    timestamp: datetime


class SensorListResponse(BaseModel):
    sensors: list[dict]


@app.get("/sensors", response_model=SensorListResponse)
def list_sensors():
    """List all available sensors."""
    return SensorListResponse(sensors=_client.get_all_sensors())


@app.get("/sensors/{sensor_id}/temperature", response_model=ReadingResponse)
def get_temperature(sensor_id: str):
    """Get the latest temperature reading for a sensor."""
    try:
        reading = _client.get_reading(sensor_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    temp_c = to_celsius(reading)
    return ReadingResponse(
        sensor_id=reading.sensor_id,
        temperature_c=round(temp_c, 2),
        temperature_f=round(celsius_to_fahrenheit(temp_c), 2),
        unit=reading.unit,
        location=reading.location,
        timestamp=reading.timestamp,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
