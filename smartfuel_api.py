from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="SmartFuel Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# MODELS
# -------------------------

class TelemetryIn(BaseModel):
    fuel_liters: float
    fuel_percent: float          # 0.0 to 1.0
    water_in_fuel: float         # your sensor value (ppm/volt/etc.)
    quality_score: float         # e.g. 0-10
    contaminants: Optional[str] = None
    recommendation: Optional[str] = None
    device_id: str = "device-1"

class TelemetryOut(TelemetryIn):
    updated_at: str

LATEST: Optional[TelemetryOut] = None
HISTORY: List[TelemetryOut] = []
MAX_HISTORY = 50

# -------------------------
# BASIC ROUTES
# -------------------------

@app.get("/")
def root():
    return {"message": "SmartFuel backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------
# REAL TELEMETRY ROUTES
# -------------------------

@app.post("/telemetry")
def push_telemetry(payload: TelemetryIn):
    global LATEST, HISTORY

    item = TelemetryOut(
        **payload.dict(),
        updated_at=datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p")
    )
    LATEST = item
    HISTORY.insert(0, item)
    HISTORY[:] = HISTORY[:MAX_HISTORY]
    return {"status": "ok", "updated_at": item.updated_at}

@app.get("/telemetry/latest")
def telemetry_latest():
    if LATEST is None:
        return {"status": "waiting", "message": "No device data yet"}
    return LATEST.dict()

@app.get("/telemetry/history")
def telemetry_history():
    return [x.dict() for x in HISTORY]

# -------------------------
# SENSORS / QUALITY (derived from telemetry)
# -------------------------

@app.get("/sensors/latest")
def sensors_latest():
    if LATEST is None:
        return {"status": "waiting", "message": "No device data yet"}
    return {
        "fuel_liters": LATEST.fuel_liters,
        "fuel_percent": LATEST.fuel_percent,
        "water_in_fuel": LATEST.water_in_fuel,
        "updated_at": LATEST.updated_at
    }

@app.get("/quality/latest")
def quality_latest():
    if LATEST is None:
        return {"status": "waiting", "message": "No device data yet"}
    return {
        "quality_score": LATEST.quality_score,
        "contaminants": LATEST.contaminants,
        "recommendation": LATEST.recommendation,
        "updated_at": LATEST.updated_at
    }

