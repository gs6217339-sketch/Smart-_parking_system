"""
backend/main.py  —  FastAPI REST API
All business logic lives here.
Frontend (Streamlit) talks to this via HTTP only.

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

import parking as pk
from database import init_db

load_dotenv()

SECRET_KEY  = os.getenv("SECRET_KEY", "smartpark-secret-key-change-in-prod")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8   # 8 hours

app = FastAPI(
    title="Smart Parking System API",
    description="FastAPI backend for Smart Parking — MongoDB",
    version="2.0.0",
)

# Allow Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Startup ──────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    ok, msg = init_db()
    if not ok:
        raise RuntimeError(f"DB init failed: {msg}")
    print(f"✅ {msg}")


# ══════════════════════════════════════════════════════════════
#  PYDANTIC SCHEMAS  (request / response shapes)
# ══════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm:  str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str

class ParkRequest(BaseModel):
    location_id:  str
    plate:        str
    owner:        str
    vehicle_type: str = "Car"

class CheckoutRequest(BaseModel):
    location_id: str
    plate:       str

class SearchRequest(BaseModel):
    plate: str

class NearbyRequest(BaseModel):
    lat:       float
    lon:       float
    radius_km: float = 5.0

class PriceCompareRequest(BaseModel):
    hours_list: List[int] = [1, 3, 6, 12, 24]


# ══════════════════════════════════════════════════════════════
#  JWT HELPERS
# ══════════════════════════════════════════════════════════════
def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")


# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════
@app.post("/auth/register", tags=["Auth"])
def register(body: RegisterRequest):
    ok, msg = pk.register_user(body.username, body.password, body.confirm)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    ok, msg = pk.login_user(form.username, form.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=msg
        )
    token = create_token(form.username)
    return TokenResponse(access_token=token, username=form.username)


@app.get("/auth/me", tags=["Auth"])
def me(user: str = Depends(get_current_user)):
    return {"username": user}


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════
@app.get("/dashboard/stats", tags=["Dashboard"])
def dashboard_stats(user: str = Depends(get_current_user)):
    return pk.get_stats()


# ══════════════════════════════════════════════════════════════
#  LOCATIONS
# ══════════════════════════════════════════════════════════════
@app.get("/locations", tags=["Locations"])
def all_locations(user: str = Depends(get_current_user)):
    locs = pk.get_all_locations()
    # Convert non-serializable types
    return [_serialize(l) for l in locs]


@app.get("/locations/{location_id}", tags=["Locations"])
def one_location(location_id: str, user: str = Depends(get_current_user)):
    loc = pk.get_location(location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    return _serialize(loc)


@app.get("/locations/{location_id}/slots", tags=["Locations"])
def location_slots(location_id: str, user: str = Depends(get_current_user)):
    slots = pk.get_slots(location_id)
    queue = pk.get_queue(location_id)
    return {
        "slots": [_serialize(s) for s in slots],
        "queue": [_serialize(q) for q in queue],
    }


@app.post("/locations/nearby", tags=["Locations"])
def nearby(body: NearbyRequest, user: str = Depends(get_current_user)):
    results = pk.get_nearby_locations(body.lat, body.lon, body.radius_km)
    return [_serialize(r) for r in results]


# ══════════════════════════════════════════════════════════════
#  PARKING
# ══════════════════════════════════════════════════════════════
@app.post("/parking/park", tags=["Parking"])
def park_vehicle(body: ParkRequest, user: str = Depends(get_current_user)):
    try:
        slot, status_str = pk.add_vehicle(
            body.location_id, body.plate,
            body.owner, body.vehicle_type, user
        )
        return {
            "status":  status_str,
            "slot":    slot,
            "plate":   body.plate.upper(),
            "message": (
                f"Vehicle {body.plate.upper()} parked at Slot #{slot}."
                if status_str == "parked"
                else f"Lot full. {body.plate.upper()} added to queue."
            )
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/parking/checkout", tags=["Parking"])
def checkout_vehicle(body: CheckoutRequest, user: str = Depends(get_current_user)):
    try:
        slot_num, charge, auto = pk.remove_vehicle(body.location_id, body.plate)
        return {
            "plate":         body.plate.upper(),
            "slot":          slot_num,
            "charge":        charge,
            "auto_assigned": auto,
            "message":       f"Checked out. Charge: ₹{charge:.2f}",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/parking/search", tags=["Parking"])
def search(body: SearchRequest, user: str = Depends(get_current_user)):
    results = pk.search_vehicle(body.plate)
    return [_serialize(r) for r in results]


# ══════════════════════════════════════════════════════════════
#  PRICE COMPARISON
# ══════════════════════════════════════════════════════════════
@app.post("/prices/compare", tags=["Prices"])
def price_compare(
    body: PriceCompareRequest,
    user: str = Depends(get_current_user)
):
    data, hours = pk.compare_prices(body.hours_list)
    cheapest    = pk.cheapest_location(data)
    return {
        "locations":  data,
        "hours_list": hours,
        "cheapest":   cheapest,
    }


# ══════════════════════════════════════════════════════════════
#  VEHICLE TYPES
# ══════════════════════════════════════════════════════════════
@app.get("/vehicle-types", tags=["Vehicle Types"])
def vehicle_types(user: str = Depends(get_current_user)):
    return pk.get_vehicle_types()


# ══════════════════════════════════════════════════════════════
#  BOOKINGS
# ══════════════════════════════════════════════════════════════
@app.get("/bookings", tags=["Bookings"])
def bookings(
    mine:  bool = False,
    limit: int  = 100,
    user:  str  = Depends(get_current_user)
):
    uid     = user if mine else None
    records = pk.get_bookings(user_id=uid, limit=limit)
    return [_serialize(r) for r in records]


# ══════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════
@app.get("/analytics", tags=["Analytics"])
def analytics(user: str = Depends(get_current_user)):
    data = pk.get_analytics()
    return _serialize_deep(data)


# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "SmartPark API", "version": "2.0"}


# ══════════════════════════════════════════════════════════════
#  SERIALIZATION HELPERS
# ══════════════════════════════════════════════════════════════
def _serialize(obj):
    """Convert datetime/Decimal → JSON-safe types."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    try:
        import decimal
        if isinstance(obj, decimal.Decimal):
            return float(obj)
    except ImportError:
        pass
    return obj


def _serialize_deep(obj):
    return _serialize(obj)
