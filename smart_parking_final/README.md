# 🅿 Smart Parking System — Separated Architecture
**Backend: FastAPI (Python)  |  Frontend: Streamlit (Python)  |  DB: CockroachDB**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                             │
│              Streamlit  (port 8501)                     │
│                                                         │
│   app.py          ← Only UI pages, no logic            │
│   api_client.py   ← All HTTP calls to backend          │
│                                                         │
│   No SQL. No DB. No business logic.                     │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTP REST API (JSON)
                       │  Authorization: Bearer <JWT>
┌──────────────────────▼──────────────────────────────────┐
│                    BACKEND                              │
│               FastAPI  (port 8000)                      │
│                                                         │
│   main.py      ← REST API routes + JWT auth            │
│   parking.py   ← Business logic (slot array, queue)    │
│   database.py  ← CockroachDB connection + schema       │
│                                                         │
│   Auto docs: http://localhost:8000/docs                 │
└──────────────────────┬──────────────────────────────────┘
                       │  psycopg2 (PostgreSQL protocol)
┌──────────────────────▼──────────────────────────────────┐
│                  DATABASE                               │
│              CockroachDB (port 26257)                   │
│                                                         │
│   users · locations · slots · queue · bookings          │
│   vehicle_types · otp_store                             │
└─────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
smart_parking_final/
├── backend/
│   ├── main.py         ← FastAPI app + all REST routes
│   ├── parking.py      ← Business logic (pure Python)
│   ├── database.py     ← CockroachDB schema + seed
│   ├── requirements.txt
│   └── .env            ← DATABASE_URL + SECRET_KEY
│
├── frontend/
│   ├── app.py          ← Streamlit UI (calls API only)
│   ├── api_client.py   ← HTTP client (requests library)
│   ├── requirements.txt
│   └── .streamlit/
│       └── config.toml ← Dark theme
│
└── README.md
```

---

## What Each Layer Does

### Backend (FastAPI)
- Receives HTTP requests from frontend
- Validates JWT tokens on every request
- Runs all business logic (parking, queue, billing)
- Talks to CockroachDB
- Returns JSON responses
- Auto docs at `/docs`

### Frontend (Streamlit)
- Shows UI pages to user
- Takes user input (forms, buttons)
- Calls backend API via `api_client.py`
- Displays data returned from API
- NO database access
- NO business logic

### Database (CockroachDB)
- Stores all data
- Only backend talks to it
- Frontend never touches it

---

## Setup & Run

### Step 1 — Backend setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "DATABASE_URL=postgresql://user:pass@host:26257/smart_parking?sslmode=verify-full&sslrootcert=ca.crt" > .env
echo "SECRET_KEY=your-random-secret-key" >> .env

# Run backend
uvicorn main:app --reload --port 8000
```
Backend running at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

### Step 2 — Frontend setup
```bash
cd frontend
pip install -r requirements.txt

# Run frontend
streamlit run app.py
```
Frontend running at: **http://localhost:8501**

### Step 3 — Open browser
Go to **http://localhost:8501**

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, get JWT token |
| GET | `/dashboard/stats` | Live stats |
| GET | `/locations` | All parking locations |
| GET | `/locations/{id}/slots` | Slot map + queue |
| POST | `/locations/nearby` | Haversine search |
| POST | `/parking/park` | Park a vehicle |
| POST | `/parking/checkout` | Checkout + billing |
| POST | `/parking/search` | Find vehicle |
| POST | `/prices/compare` | Compare all rates |
| GET | `/vehicle-types` | All vehicle types |
| GET | `/bookings` | Booking history |
| GET | `/analytics` | Revenue + charts data |
| GET | `/health` | Backend status |

---

## Why Separated?

| Reason | Benefit |
|--------|---------|
| Independent deployment | Backend aur frontend alag-alag deploy ho sakte hain |
| Security | DB credentials sirf backend ke paas hain |
| Scalability | Ek backend, multiple frontends ho sakte hain |
| Testing | API ko independently test kar sakte ho |
| Industry standard | Real companies aise hi banate hain |
