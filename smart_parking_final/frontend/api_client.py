"""
frontend/api_client.py
HTTP client — Streamlit calls ONLY these functions.
No database, no SQL, no business logic here.
All data comes from the FastAPI backend.
"""

import requests
import streamlit as st

BASE_URL = "http://localhost:8000"


def _headers():
    """Attach JWT token to every request."""
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path: str, params: dict = None):
    try:
        r = requests.get(f"{BASE_URL}{path}",
                         headers=_headers(), params=params, timeout=10)
        if r.status_code == 401:
            st.session_state.logged_in = False
            st.warning("Session expired. Please login again.")
            return None
        return r.json() if r.ok else None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. "
                 "Make sure FastAPI is running on port 8000.")
        return None


def _post(path: str, data: dict = None, form: dict = None):
    try:
        if form:
            r = requests.post(f"{BASE_URL}{path}",
                              data=form, headers=_headers(), timeout=10)
        else:
            r = requests.post(f"{BASE_URL}{path}",
                              json=data, headers=_headers(), timeout=10)
        return r.json(), r.ok, r.status_code
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend.")
        return None, False, 0


# ── Auth ─────────────────────────────────────────────────────
def api_register(username, password, confirm):
    resp, ok, _ = _post("/auth/register", {
        "username": username, "password": password, "confirm": confirm
    })
    if ok:
        return True, resp.get("message", "Registered!")
    return False, resp.get("detail", "Registration failed.")


def api_login(username, password):
    resp, ok, code = _post("/auth/login", form={
        "username": username, "password": password
    })
    if ok and resp:
        return True, resp.get("access_token"), resp.get("username")
    detail = resp.get("detail", "Login failed.") if resp else "Login failed."
    return False, None, detail


# ── Dashboard ────────────────────────────────────────────────
def api_stats():
    return _get("/dashboard/stats") or {}


# ── Locations ────────────────────────────────────────────────
def api_locations():
    return _get("/locations") or []


def api_location(location_id):
    return _get(f"/locations/{location_id}") or {}


def api_slots(location_id):
    return _get(f"/locations/{location_id}/slots") or \
           {"slots": [], "queue": []}


def api_nearby(lat, lon, radius_km=5.0):
    resp, ok, _ = _post("/locations/nearby", {
        "lat": lat, "lon": lon, "radius_km": radius_km
    })
    return resp if ok else []


# ── Parking ──────────────────────────────────────────────────
def api_park(location_id, plate, owner, vehicle_type="Car"):
    resp, ok, _ = _post("/parking/park", {
        "location_id":  location_id,
        "plate":        plate,
        "owner":        owner,
        "vehicle_type": vehicle_type,
    })
    if ok:
        return True, resp
    return False, resp.get("detail", "Failed.") if resp else "Failed."


def api_checkout(location_id, plate):
    resp, ok, _ = _post("/parking/checkout", {
        "location_id": location_id, "plate": plate
    })
    if ok:
        return True, resp
    return False, resp.get("detail", "Failed.") if resp else "Failed."


def api_search(plate):
    resp, ok, _ = _post("/parking/search", {"plate": plate})
    return resp if ok else []


# ── Prices ───────────────────────────────────────────────────
def api_compare_prices(hours_list=None):
    if hours_list is None:
        hours_list = [1, 3, 6, 12, 24]
    resp, ok, _ = _post("/prices/compare", {"hours_list": hours_list})
    return resp if ok else {}


# ── Vehicle Types ────────────────────────────────────────────
def api_vehicle_types():
    return _get("/vehicle-types") or []


# ── Bookings ─────────────────────────────────────────────────
def api_bookings(mine=False, limit=100):
    return _get("/bookings", {"mine": mine, "limit": limit}) or []


# ── Analytics ────────────────────────────────────────────────
def api_analytics():
    return _get("/analytics") or {}


# ── Health ───────────────────────────────────────────────────
def api_health():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        return r.ok
    except Exception:
        return False
