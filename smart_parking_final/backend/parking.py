"""
backend/parking.py
Pure business logic — no UI, no Streamlit.
Called only by FastAPI routes.
Data Structures: Slot Array, FIFO Queue, Haversine, Booking Log
CockroachDB backend via psycopg2.
"""

import math
from datetime import datetime, timezone
from database import get_db


# ── Billing ──────────────────────────────────────────────────
def calc_charge(entry_time: datetime, rate_per_hour: float = 30.0) -> float:
    now = datetime.now(timezone.utc)
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    seconds = (now - entry_time).total_seconds()
    hours   = max(1.0, math.ceil(seconds / 3600))
    return round(hours * rate_per_hour, 2)


def estimate_charge(hours: float, rate_per_hour: float) -> float:
    return round(max(1.0, math.ceil(hours)) * rate_per_hour, 2)


# ── Haversine ────────────────────────────────────────────────
def calc_distance(lat1, lon1, lat2, lon2) -> float:
    R      = 6371.0
    to_rad = math.pi / 180
    dLat   = (lat2 - lat1) * to_rad
    dLon   = (lon2 - lon1) * to_rad
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(lat1 * to_rad) * math.cos(lat2 * to_rad) *
         math.sin(dLon / 2) ** 2)
    return round(2 * R * math.asin(math.sqrt(a)), 2)


# ── Auth ─────────────────────────────────────────────────────
def register_user(username: str, password: str, confirm: str):
    from werkzeug.security import generate_password_hash
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if password != confirm:
        return False, "Passwords do not match."
    try:
        hashed = generate_password_hash(password)
        with get_db() as cur:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed)
            )
        return True, f"Account '{username}' created!"
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, "Username already exists."
        return False, str(e)


def login_user(username: str, password: str):
    from werkzeug.security import check_password_hash
    try:
        with get_db() as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s", (username.strip(),)
            )
            user = cur.fetchone()
        if user and check_password_hash(user["password"], password):
            return True, "Login successful!"
        return False, "Invalid username or password."
    except Exception as e:
        return False, str(e)


# ── Locations ────────────────────────────────────────────────
def get_all_locations():
    with get_db() as cur:
        cur.execute("""
            SELECT l.*,
                   COUNT(s.id) FILTER (WHERE s.is_occupied)      AS occupied,
                   COUNT(s.id) FILTER (WHERE NOT s.is_occupied)  AS free_slots,
                   (SELECT COUNT(*) FROM queue q
                    WHERE q.location_id = l.location_id)         AS queue_count
            FROM   locations l
            LEFT JOIN slots s ON s.location_id = l.location_id
            GROUP BY l.id, l.location_id, l.name, l.address,
                     l.latitude, l.longitude, l.total_slots, l.rate_per_hour
            ORDER BY l.name
        """)
        return [dict(r) for r in cur.fetchall()]


def get_location(location_id: str):
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM locations WHERE location_id = %s", (location_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_nearby_locations(lat: float, lon: float, radius_km: float = 5.0):
    locs   = get_all_locations()
    nearby = []
    for loc in locs:
        dist = calc_distance(lat, lon, loc["latitude"], loc["longitude"])
        if dist <= radius_km:
            nearby.append({**loc, "distance_km": dist})
    return sorted(nearby, key=lambda x: x["distance_km"])


# ── Slot Array ───────────────────────────────────────────────
def get_slots(location_id: str):
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM slots WHERE location_id=%s ORDER BY slot_number",
            (location_id,)
        )
        return [dict(r) for r in cur.fetchall()]


# ── FIFO Queue ───────────────────────────────────────────────
def get_queue(location_id: str):
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM queue WHERE location_id=%s ORDER BY queued_at",
            (location_id,)
        )
        return [dict(r) for r in cur.fetchall()]


# ── Add Vehicle ──────────────────────────────────────────────
def add_vehicle(location_id: str, plate: str, owner: str,
                vehicle_type: str = "Car", user_id: str = "guest"):
    plate = plate.strip().upper()
    if not plate or not owner.strip():
        raise ValueError("Plate and owner name are required.")

    with get_db() as cur:
        cur.execute(
            "SELECT 1 FROM slots WHERE location_id=%s AND vehicle_plate=%s",
            (location_id, plate)
        )
        if cur.fetchone():
            raise ValueError(f"Vehicle {plate} already parked here.")

        cur.execute(
            "SELECT 1 FROM queue WHERE location_id=%s AND vehicle_plate=%s",
            (location_id, plate)
        )
        if cur.fetchone():
            raise ValueError(f"Vehicle {plate} already in queue.")

        cur.execute(
            "SELECT id, slot_number FROM slots "
            "WHERE location_id=%s AND is_occupied=FALSE "
            "ORDER BY slot_number LIMIT 1",
            (location_id,)
        )
        free = cur.fetchone()

        if free:
            now = datetime.now(timezone.utc)
            cur.execute(
                "UPDATE slots SET is_occupied=TRUE, vehicle_plate=%s, "
                "vehicle_owner=%s, vehicle_type=%s, entry_time=%s WHERE id=%s",
                (plate, owner.strip(), vehicle_type, now, free["id"])
            )
            slot_num = free["slot_number"]
            cur.execute(
                "INSERT INTO bookings (user_id, location_id, location_name, "
                "vehicle_plate, slot_number) "
                "SELECT %s,%s,name,%s,%s FROM locations WHERE location_id=%s",
                (user_id, location_id, plate, slot_num, location_id)
            )
            return slot_num, "parked"
        else:
            cur.execute(
                "INSERT INTO queue (location_id, vehicle_plate, vehicle_owner) "
                "VALUES (%s,%s,%s)",
                (location_id, plate, owner.strip())
            )
            cur.execute(
                "INSERT INTO bookings (user_id, location_id, location_name, "
                "vehicle_plate, slot_number) "
                "SELECT %s,%s,name,%s,NULL FROM locations WHERE location_id=%s",
                (user_id, location_id, plate, location_id)
            )
            return None, "queued"


# ── Remove Vehicle ───────────────────────────────────────────
def remove_vehicle(location_id: str, plate: str):
    plate = plate.strip().upper()
    with get_db() as cur:
        cur.execute(
            "SELECT id, slot_number, entry_time, vehicle_type FROM slots "
            "WHERE location_id=%s AND vehicle_plate=%s AND is_occupied=TRUE",
            (location_id, plate)
        )
        slot = cur.fetchone()
        if not slot:
            raise ValueError(f"Vehicle {plate} not found.")

        cur.execute(
            "SELECT rate_per_hour FROM locations WHERE location_id=%s",
            (location_id,)
        )
        loc_row = cur.fetchone()
        rate    = float(loc_row["rate_per_hour"]) if loc_row else 30.0
        charge  = calc_charge(slot["entry_time"], rate)

        cur.execute(
            "UPDATE slots SET is_occupied=FALSE, vehicle_plate=NULL, "
            "vehicle_owner=NULL, vehicle_type=NULL, entry_time=NULL WHERE id=%s",
            (slot["id"],)
        )
        cur.execute(
            "UPDATE bookings SET checked_out_at=now(), charge=%s "
            "WHERE vehicle_plate=%s AND location_id=%s AND checked_out_at IS NULL",
            (charge, plate, location_id)
        )

        cur.execute(
            "SELECT id, vehicle_plate, vehicle_owner FROM queue "
            "WHERE location_id=%s ORDER BY queued_at LIMIT 1",
            (location_id,)
        )
        next_v        = cur.fetchone()
        auto_assigned = None
        if next_v:
            now = datetime.now(timezone.utc)
            cur.execute(
                "UPDATE slots SET is_occupied=TRUE, vehicle_plate=%s, "
                "vehicle_owner=%s, entry_time=%s WHERE id=%s",
                (next_v["vehicle_plate"], next_v["vehicle_owner"],
                 now, slot["id"])
            )
            cur.execute("DELETE FROM queue WHERE id=%s", (next_v["id"],))
            auto_assigned = next_v["vehicle_plate"]

        return slot["slot_number"], charge, auto_assigned


# ── Search ───────────────────────────────────────────────────
def search_vehicle(plate: str):
    plate   = plate.strip().upper()
    results = []
    with get_db() as cur:
        cur.execute(
            "SELECT s.*, l.name AS location_name, l.address, l.rate_per_hour "
            "FROM slots s JOIN locations l ON l.location_id=s.location_id "
            "WHERE s.vehicle_plate=%s AND s.is_occupied=TRUE",
            (plate,)
        )
        for row in cur.fetchall():
            r                  = dict(row)
            r["status"]        = "parked"
            r["charge_so_far"] = calc_charge(r["entry_time"], r["rate_per_hour"])
            results.append(r)

        cur.execute(
            "SELECT q.*, l.name AS location_name, l.address "
            "FROM queue q JOIN locations l ON l.location_id=q.location_id "
            "WHERE q.vehicle_plate=%s",
            (plate,)
        )
        for row in cur.fetchall():
            results.append({**dict(row), "status": "queued"})
    return results


# ── Price Comparison ─────────────────────────────────────────
def compare_prices(hours_list=None):
    if hours_list is None:
        hours_list = [1, 3, 6, 12, 24]
    locs   = get_all_locations()
    result = []
    for loc in locs:
        rate  = loc.get("rate_per_hour", 30.0)
        entry = {
            "location_id":   loc["location_id"],
            "name":          loc["name"],
            "address":       loc["address"],
            "rate_per_hour": rate,
            "free_slots":    loc["free_slots"],
            "total_slots":   loc["total_slots"],
            "queue_count":   loc["queue_count"],
        }
        for h in hours_list:
            entry[f"{h}h"] = estimate_charge(h, rate)
        result.append(entry)
    result.sort(key=lambda x: x["rate_per_hour"])
    return result, hours_list


def cheapest_location(locs_with_prices):
    available = [l for l in locs_with_prices if l["free_slots"] > 0]
    if not available:
        return min(locs_with_prices, key=lambda x: x["rate_per_hour"])
    return min(available, key=lambda x: x["rate_per_hour"])


# ── Vehicle Types ────────────────────────────────────────────
def get_vehicle_types():
    with get_db() as cur:
        cur.execute("SELECT * FROM vehicle_types ORDER BY rate_per_hour")
        return [dict(r) for r in cur.fetchall()]


def get_vehicle_rate(vehicle_type: str) -> float:
    with get_db() as cur:
        cur.execute(
            "SELECT rate_per_hour FROM vehicle_types WHERE type_name=%s",
            (vehicle_type,)
        )
        row = cur.fetchone()
        return float(row["rate_per_hour"]) if row else 30.0


# ── Bookings ─────────────────────────────────────────────────
def get_bookings(user_id: str = None, limit: int = 100):
    with get_db() as cur:
        if user_id:
            cur.execute(
                "SELECT * FROM bookings WHERE user_id=%s "
                "ORDER BY booked_at DESC LIMIT %s",
                (user_id, limit)
            )
        else:
            cur.execute(
                "SELECT * FROM bookings ORDER BY booked_at DESC LIMIT %s",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]


# ── Dashboard Stats ──────────────────────────────────────────
def get_stats():
    with get_db() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM users");                        users    = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM locations");                    locs     = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM slots WHERE is_occupied=TRUE"); occupied = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM slots WHERE is_occupied=FALSE");free     = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM queue");                        queued   = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM bookings");                     bookings = cur.fetchone()["c"]
    return {
        "users": users, "locations": locs, "occupied": occupied,
        "free": free, "queued": queued, "bookings": bookings,
    }


# ── Analytics ────────────────────────────────────────────────
def get_analytics():
    with get_db() as cur:
        cur.execute("""
            SELECT DATE(booked_at) AS day,
                   COUNT(*) AS total_bookings,
                   COALESCE(SUM(charge),0) AS revenue
            FROM bookings
            WHERE booked_at >= now() - INTERVAL '7 days'
            GROUP BY DATE(booked_at) ORDER BY day
        """)
        daily = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COALESCE(vehicle_type,'Car') AS vehicle_type,
                   COUNT(*) AS total
            FROM slots GROUP BY vehicle_type ORDER BY total DESC
        """)
        vtype_all = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT l.name,
                   COUNT(s.id) FILTER (WHERE s.is_occupied)      AS occupied,
                   COUNT(s.id) FILTER (WHERE NOT s.is_occupied)  AS free,
                   l.total_slots, l.rate_per_hour,
                   COALESCE((SELECT SUM(charge) FROM bookings b
                    WHERE b.location_id=l.location_id
                    AND b.checked_out_at IS NOT NULL),0) AS total_revenue
            FROM locations l
            LEFT JOIN slots s ON s.location_id=l.location_id
            GROUP BY l.name, l.total_slots, l.rate_per_hour, l.location_id
            ORDER BY total_revenue DESC
        """)
        loc_stats = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT EXTRACT(HOUR FROM booked_at) AS hour,
                   COUNT(*) AS bookings
            FROM bookings GROUP BY hour ORDER BY hour
        """)
        peak_hours = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COALESCE(AVG(
                EXTRACT(EPOCH FROM (checked_out_at - booked_at))/3600
            ),0) AS avg_hours
            FROM bookings WHERE checked_out_at IS NOT NULL
        """)
        avg_dur   = float(cur.fetchone()["avg_hours"])

        cur.execute("""
            SELECT COALESCE(SUM(charge),0) AS total
            FROM bookings WHERE checked_out_at IS NOT NULL
        """)
        total_rev = float(cur.fetchone()["total"])

        cur.execute("""
            SELECT COALESCE(SUM(charge),0) AS total FROM bookings
            WHERE DATE(checked_out_at)=CURRENT_DATE
        """)
        today_rev = float(cur.fetchone()["total"])

    return {
        "daily":         daily,
        "vtype_all":     vtype_all,
        "loc_stats":     loc_stats,
        "peak_hours":    peak_hours,
        "avg_duration":  round(avg_dur, 2),
        "total_revenue": round(total_rev, 2),
        "today_revenue": round(today_rev, 2),
    }
