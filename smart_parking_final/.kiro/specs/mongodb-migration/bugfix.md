# Bugfix Requirements Document

## Introduction

The Smart Parking System backend cannot start because it depends on CockroachDB
(a PostgreSQL-compatible distributed database) via the `psycopg2` driver. The
CockroachDB instance is unavailable and cannot be configured in the current
environment. As a result, `database.py` fails to connect on import, `init_db()`
raises an exception at startup, and every API endpoint is unreachable.

The fix migrates the entire database layer — `database.py` and `parking.py` —
from CockroachDB/psycopg2 to MongoDB/PyMongo. The FastAPI routes (`main.py`),
Streamlit frontend (`frontend/app.py`), and HTTP client (`frontend/api_client.py`)
are **not** changed. The external contract (API shape, response structure) remains
identical.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the backend process starts THEN the system fails with a connection error
    because `psycopg2.connect()` cannot reach the CockroachDB host specified in
    `DATABASE_URL`.

1.2 WHEN `DATABASE_URL` is missing or empty THEN the system raises an
    `OperationalError` (psycopg2) during `init_db()`, preventing the FastAPI
    app from completing its startup event.

1.3 WHEN any API endpoint is called THEN the system returns a 500 Internal
    Server Error because `get_db()` attempts a psycopg2 connection that
    always fails in the current environment.

1.4 WHEN `database.py` is imported THEN the system loads the `psycopg2` module,
    which is coupled to PostgreSQL wire protocol and incompatible with MongoDB.

1.5 WHEN `parking.py` executes business logic THEN the system issues raw SQL
    statements (including CockroachDB-specific syntax such as `STRING` type,
    `gen_random_uuid()`, `FILTER (WHERE ...)`, and `INTERVAL` literals) that
    have no equivalent in a non-SQL data store.

1.6 WHEN `init_db()` is called THEN the system attempts to execute DDL
    (`CREATE TABLE IF NOT EXISTS`) against a CockroachDB cluster, which is
    unavailable.

### Expected Behavior (Correct)

2.1 WHEN the backend process starts THEN the system SHALL connect to MongoDB
    using `MONGODB_URI` from the environment (defaulting to
    `mongodb://localhost:27017`) via `pymongo.MongoClient`, and complete
    startup without errors.

2.2 WHEN `MONGODB_URI` is missing or empty THEN the system SHALL fall back to
    `mongodb://localhost:27017` and attempt to connect, raising a clear
    `ConnectionFailure` only if MongoDB itself is unreachable.

2.3 WHEN any API endpoint is called THEN the system SHALL execute the
    corresponding PyMongo operation against the `smart_parking` database
    and return the same JSON response shape as before.

2.4 WHEN `database.py` is imported THEN the system SHALL import `pymongo` (not
    `psycopg2`) and expose a `get_db()` context manager that yields a PyMongo
    database handle.

2.5 WHEN `parking.py` executes business logic THEN the system SHALL use PyMongo
    collection methods (`find_one`, `find`, `insert_one`, `update_one`,
    `delete_one`, `aggregate`) instead of SQL queries, and shall use
    `uuid.uuid4()` for ID generation and `datetime.now(timezone.utc)` for
    timestamps.

2.6 WHEN `init_db()` is called THEN the system SHALL create MongoDB collections
    (`users`, `locations`, `slots`, `queue`, `bookings`, `vehicle_types`),
    apply the required indexes (e.g. unique index on `users.username`,
    compound unique index on `slots.location_id + slot_number`), and seed the
    three default locations and their slots if they do not already exist —
    without executing any SQL DDL.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user registers with a unique username THEN the system SHALL CONTINUE
    TO create the account and return a success message.

3.2 WHEN a user registers with a duplicate username THEN the system SHALL
    CONTINUE TO return an error indicating the username already exists.

3.3 WHEN a user logs in with valid credentials THEN the system SHALL CONTINUE
    TO return a JWT access token with the same structure and expiry.

3.4 WHEN a vehicle is parked at a location with a free slot THEN the system
    SHALL CONTINUE TO occupy the lowest-numbered free slot and create a
    booking record.

3.5 WHEN a vehicle is parked at a fully occupied location THEN the system
    SHALL CONTINUE TO add the vehicle to the FIFO queue and create a
    booking record with `slot_number = null`.

3.6 WHEN a parked vehicle is checked out THEN the system SHALL CONTINUE TO
    free the slot, calculate the charge (minimum 1 hour, rounded up),
    update the booking record with `checked_out_at` and `charge`, and
    auto-assign the slot to the next vehicle in the queue if one exists.

3.7 WHEN nearby locations are queried with a latitude, longitude, and radius
    THEN the system SHALL CONTINUE TO return only locations within the
    specified radius, sorted by ascending distance, using the Haversine
    formula.

3.8 WHEN the price comparison endpoint is called THEN the system SHALL
    CONTINUE TO return all locations with estimated charges for each
    requested duration, and identify the cheapest available location.

3.9 WHEN the analytics endpoint is called THEN the system SHALL CONTINUE TO
    return daily booking counts, revenue aggregates, per-location stats,
    peak-hour distribution, average duration, total revenue, and
    today's revenue.

3.10 WHEN the `/health` endpoint is called THEN the system SHALL CONTINUE TO
     return `{"status": "ok"}` without requiring authentication.

3.11 WHEN the FastAPI routes in `main.py` call functions in `parking.py`
     THEN the system SHALL CONTINUE TO receive Python dicts and lists with
     the same keys as before, so that no changes to `main.py` are needed.

3.12 WHEN the Streamlit frontend calls the FastAPI API THEN the system SHALL
     CONTINUE TO receive HTTP responses with identical JSON shapes, so that
     no changes to `frontend/app.py` or `frontend/api_client.py` are needed.

---

## Bug Condition

**Bug Condition Function:**

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type SystemStartupOrAPICall
  OUTPUT: boolean

  // The bug is triggered whenever the backend tries to use the database layer
  RETURN X requires a database operation
         AND the database driver is psycopg2
         AND CockroachDB is unavailable
END FUNCTION
```

**Fix Checking Property:**

```pascal
// Property: Fix Checking — backend starts and serves requests
FOR ALL X WHERE isBugCondition(X) DO
  result ← handleWithMongoDB(X)
  ASSERT result does not raise ConnectionError
  ASSERT result returns expected data shape
END FOR
```

**Preservation Checking Property:**

```pascal
// Property: Preservation Checking — existing behavior unchanged
FOR ALL X WHERE NOT isBugCondition(X) DO
  // i.e., all business logic paths (auth, park, checkout, search, analytics)
  ASSERT F_mongo(X) produces same external output shape as F_cockroachdb(X)
END FOR
```
