"""
database.py — CockroachDB connection + schema bootstrap
Pure Python, psycopg2 driver (PostgreSQL-compatible).
Connection: postgresql://root@localhost:26257/smart_parking?sslmode=disable
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root@localhost:26257/smart_parking?sslmode=disable")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def get_db():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
        id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        username   STRING(50)  NOT NULL UNIQUE,
        password   STRING(256) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",

    """CREATE TABLE IF NOT EXISTS locations (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        location_id   STRING(50)  NOT NULL UNIQUE,
        name          STRING(100) NOT NULL,
        address       STRING(200) NOT NULL,
        latitude      FLOAT8      NOT NULL,
        longitude     FLOAT8      NOT NULL,
        total_slots   INT         NOT NULL DEFAULT 10,
        rate_per_hour FLOAT8      NOT NULL DEFAULT 30.0
    )""",

    """CREATE TABLE IF NOT EXISTS vehicle_types (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        type_name     STRING(50)  NOT NULL UNIQUE,
        icon          STRING(10)  NOT NULL DEFAULT '🚗',
        rate_per_hour FLOAT8      NOT NULL DEFAULT 30.0
    )""",

    """CREATE TABLE IF NOT EXISTS slots (
        id            UUID       PRIMARY KEY DEFAULT gen_random_uuid(),
        location_id   STRING(50) NOT NULL REFERENCES locations(location_id),
        slot_number   INT        NOT NULL,
        is_occupied   BOOL       NOT NULL DEFAULT FALSE,
        vehicle_plate STRING(50),
        vehicle_owner STRING(50),
        vehicle_type  STRING(50),
        entry_time    TIMESTAMPTZ,
        UNIQUE (location_id, slot_number)
    )""",

    """CREATE TABLE IF NOT EXISTS queue (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        location_id   STRING(50)  NOT NULL REFERENCES locations(location_id),
        vehicle_plate STRING(50)  NOT NULL,
        vehicle_owner STRING(50)  NOT NULL,
        queued_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",

    """CREATE TABLE IF NOT EXISTS bookings (
        id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id        STRING(50)  NOT NULL,
        location_id    STRING(50)  NOT NULL,
        location_name  STRING(100) NOT NULL,
        vehicle_plate  STRING(50)  NOT NULL,
        slot_number    INT,
        booked_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        checked_out_at TIMESTAMPTZ,
        charge         FLOAT8
    )""",

    """CREATE TABLE IF NOT EXISTS otp_store (
        id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        username   STRING(50)  NOT NULL,
        otp        STRING(10)  NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
]

SEED_VEHICLE_TYPES = [
    ("Bike",  "🏍",  10.0),
    ("Car",   "🚗",  30.0),
    ("SUV",   "🚙",  40.0),
    ("Truck", "🚛",  60.0),
]

SEED_LOCATIONS = [
    ("loc-a", "Central Plaza Parking", "MG Road, Bengaluru",       12.9716, 77.5946, 10, 30.0),
    ("loc-b", "Trinity Tower Garage",  "Trinity Circle, Bengaluru", 12.9750, 77.6000,  8, 25.0),
    ("loc-c", "Cubbon Park Lot",       "Cubbon Park, Bengaluru",    12.9763, 77.5929, 12, 20.0),
]


def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()

        for stmt in SCHEMA_STATEMENTS:
            cur.execute(stmt)
        conn.commit()

        # Seed vehicle types
        for type_name, icon, rate in SEED_VEHICLE_TYPES:
            cur.execute(
                "INSERT INTO vehicle_types (type_name, icon, rate_per_hour) "
                "VALUES (%s,%s,%s) ON CONFLICT (type_name) DO NOTHING",
                (type_name, icon, rate)
            )

        # Seed locations + slots
        for loc_id, name, addr, lat, lon, total, rate in SEED_LOCATIONS:
            cur.execute(
                "INSERT INTO locations (location_id, name, address, latitude, longitude, total_slots, rate_per_hour) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (location_id) DO NOTHING",
                (loc_id, name, addr, lat, lon, total, rate)
            )
            for sn in range(1, total + 1):
                cur.execute(
                    "INSERT INTO slots (location_id, slot_number) "
                    "VALUES (%s,%s) ON CONFLICT (location_id, slot_number) DO NOTHING",
                    (loc_id, sn)
                )

        conn.commit()
        cur.close()
        return True, "Database ready!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
