from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Path
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from config import DEMO_MODE, API_BASE_URL, API_KEY
from temperature_sensor import (
    SensorAPIBase,
    SensorError,
    SensorNotFoundError,
    MockTemperatureSensorAPI,
    TemperatureSensorAPI,
    celsius_to_fahrenheit,
    to_celsius,
)


def make_client() -> SensorAPIBase:
    if DEMO_MODE:
        return MockTemperatureSensorAPI()
    return TemperatureSensorAPI(API_BASE_URL, API_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = make_client()
    yield
    app.state.client.close()


app = FastAPI(title="Temperature Sensor API", version="1.0.0", lifespan=lifespan)


def get_client() -> SensorAPIBase:
    return app.state.client


class ReadingResponse(BaseModel):
    sensor_id: str
    temperature_c: float
    temperature_f: float
    unit: str
    location: Optional[str]
    timestamp: datetime


class SensorListResponse(BaseModel):
    sensors: list[dict]


class HealthResponse(BaseModel):
    status: str
    mode: str


@app.get("/health", response_model=HealthResponse)
def health():
    """Service health check."""
    return HealthResponse(status="ok", mode="demo" if DEMO_MODE else "live")


@app.get("/sensors", response_model=SensorListResponse)
def list_sensors(client: SensorAPIBase = Depends(get_client)):
    """List all available sensors."""
    try:
        return SensorListResponse(sensors=client.get_all_sensors())
    except SensorError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/sensors/{sensor_id}/temperature", response_model=ReadingResponse)
def get_temperature(
    sensor_id: str = Path(pattern=r"^[\w-]+$", description="Sensor identifier"),
    client: SensorAPIBase = Depends(get_client),
):
    """Get the latest temperature reading for a sensor."""
    known = {s["id"] for s in client.get_all_sensors()}
    if known and sensor_id not in known:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found")
    try:
        reading = client.get_reading(sensor_id)
    except SensorNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found")
    except SensorError as e:
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
