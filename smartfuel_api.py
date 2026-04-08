from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# FIREBASE SETUP (FIXED)
# -------------------------

import os
import json

def init_firebase():
    if not firebase_admin._apps:
        firebase_config = os.environ.get("FIREBASE_CONFIG")

        if not firebase_config:
            raise Exception("FIREBASE_CONFIG not found")

        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)

        firebase_admin.initialize_app(cred)

    return firestore.client()

    return firestore.client()


db = init_firebase()

# -------------------------
# FASTAPI APP
# -------------------------

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
    fuel_percent: float
    water_in_fuel: float
    quality_score: float
    contaminants: Optional[str] = None
    recommendation: Optional[str] = None
    device_id: str = "device-1"

class TelemetryOut(TelemetryIn):
    updated_at: str

LATEST: Optional[TelemetryOut] = None
HISTORY: List[TelemetryOut] = []
MAX_HISTORY = 50

# -------------------------
# HELPERS
# -------------------------

def now_string():
    return datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p")

def telemetry_to_dict(item: TelemetryOut):
    return {
        "fuel_liters": item.fuel_liters,
        "fuel_percent": item.fuel_percent,
        "water_in_fuel": item.water_in_fuel,
        "quality_score": item.quality_score,
        "contaminants": item.contaminants,
        "recommendation": item.recommendation,
        "device_id": item.device_id,
        "updated_at": item.updated_at,
        "server_timestamp": firestore.SERVER_TIMESTAMP,
    }

def save_telemetry_to_firestore(item: TelemetryOut):
    data = telemetry_to_dict(item)

    # latest
    db.collection("telemetry").document("latest").set(data)

    # history
    db.collection("telemetry_history").add(data)

    # sensors
    db.collection("sensors").document("latest").set({
        "fuel_liters": item.fuel_liters,
        "fuel_percent": item.fuel_percent,
        "water_in_fuel": item.water_in_fuel,
        "updated_at": item.updated_at,
        "server_timestamp": firestore.SERVER_TIMESTAMP,
    })

    # quality
    db.collection("quality").document("latest").set({
        "quality_score": item.quality_score,
        "contaminants": item.contaminants,
        "recommendation": item.recommendation,
        "updated_at": item.updated_at,
        "server_timestamp": firestore.SERVER_TIMESTAMP,
    })

# -------------------------
# ROUTES
# -------------------------

@app.get("/")
def root():
    return {"message": "SmartFuel backend with Firebase is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/firebase-test")
def firebase_test():
    try:
        db.collection("test").add({"status": "working"})
        return {"status": "ok", "message": "Firebase connected successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# -------------------------
# TELEMETRY
# -------------------------

@app.post("/telemetry")
def push_telemetry(payload: TelemetryIn):
    global LATEST, HISTORY

    item = TelemetryOut(
        **payload.dict(),
        updated_at=now_string()
    )

    LATEST = item
    HISTORY.insert(0, item)
    HISTORY[:] = HISTORY[:MAX_HISTORY]

    try:
        save_telemetry_to_firestore(item)
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

    return {"status": "ok", "updated_at": item.updated_at}

@app.get("/telemetry/latest")
def telemetry_latest():
    if LATEST is None:
        return {"status": "waiting", "message": "No data yet"}
    return LATEST.dict()

@app.get("/telemetry/history")
def telemetry_history():
    return [x.dict() for x in HISTORY]

# -------------------------
# SENSORS / QUALITY
# -------------------------

@app.get("/sensors/latest")
def sensors_latest():
    if LATEST is None:
        return {"status": "waiting"}
    return {
        "fuel_liters": LATEST.fuel_liters,
        "fuel_percent": LATEST.fuel_percent,
        "water_in_fuel": LATEST.water_in_fuel,
        "updated_at": LATEST.updated_at
    }

@app.get("/quality/latest")
def quality_latest():
    if LATEST is None:
        return {"status": "waiting"}
    return {
        "quality_score": LATEST.quality_score,
        "contaminants": LATEST.contaminants,
        "recommendation": LATEST.recommendation,
        "updated_at": LATEST.updated_at
    }