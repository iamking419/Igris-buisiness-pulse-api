# IGRIS Business Pulse API

Production-ready FastAPI backend for the **IGRIS Business Pulse** research survey.

This API matches the existing frontend contract exactly.  
Frontend → FastAPI → PostgreSQL.

---

## What it is

IGRIS Business Pulse is a research initiative by IGRIS Technologies.  
This backend stores survey responses from Nigerian businesses and powers the admin research dashboard.

---

## Requirements

- Python 3.10+
- PostgreSQL 13+
- pip

---

## Installation

```bash
cd igris-business-pulse-api
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Environment variables

Copy the example file and edit values:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/igris_business_pulse` |
| `JWT_SECRET_KEY` | Secret for signing JWTs (long random string) | `change-this-in-production...` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin password (hashed on first startup) | `change-this-in-production` |
| `FRONTEND_ORIGIN` | Allowed CORS origin | `http://localhost:5500` |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes | `1440` (24h) |

`.env` is gitignored. Never commit real credentials.

---

## PostgreSQL setup

```bash
# Create the database (once)
createdb igris_business_pulse
# or via psql:
# CREATE DATABASE igris_business_pulse;
```

Update `DATABASE_URL` in `.env` to match your credentials.

Tables are created automatically on first startup (no separate migration step required for this project).

---

## Run locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API base: `http://localhost:8000/api/v1`
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

On first start the admin account is created from `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Liveness |
| POST | `/api/v1/survey/responses` | No | Submit survey |
| POST | `/api/v1/admin/login` | No | Admin login → JWT |
| GET | `/api/v1/admin/me` | Bearer | Current admin |
| POST | `/api/v1/admin/logout` | Bearer | Logout (client discards token) |
| GET | `/api/v1/admin/responses` | Bearer | List + filter responses |
| GET | `/api/v1/admin/responses/{id}` | Bearer | Single response by code |
| GET | `/api/v1/admin/insights` | Bearer | Aggregated insights |
| GET | `/api/v1/admin/export` | Bearer | CSV download |

### Query filters for `/admin/responses`

- `business_type`
- `challenge`
- `contact_opt_in` (`true` / `false`)
- `search` (free text)
- `limit` (1–200, default 50)
- `offset` (default 0)

---

## Authentication

1. `POST /api/v1/admin/login` with `{ "password": "..." }`
2. Receive `{ "access_token": "...", "token_type": "bearer" }`
3. Send `Authorization: Bearer <token>` on protected routes

JWTs expire after `JWT_EXPIRE_MINUTES`.  
Logout is client-side (discard the token). No server-side blacklist.

---

## Example curl commands

```bash
# Health
curl http://localhost:8000/api/v1/health

# Submit a survey response
curl -X POST http://localhost:8000/api/v1/survey/responses \
  -H "Content-Type: application/json" \
  -d '{
    "business_type": "Retail",
    "customer_channels": ["WhatsApp"],
    "biggest_challenge": "Managing orders",
    "time_consuming_task": "Order taking",
    "order_management": "WhatsApp",
    "payment_tracking": "Notebook / paper",
    "technology_used": ["WhatsApp Business"],
    "digital_barriers": ["Cost"],
    "desired_improvement": "Easier order tracking",
    "contact_permission": true,
    "contact": "owner@example.com"
  }'

# Admin login
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password": "change-this-in-production"}'

# Use the token (replace TOKEN)
export TOKEN=eyJ...

curl http://localhost:8000/api/v1/admin/me \
  -H "Authorization: Bearer $TOKEN"

curl "http://localhost:8000/api/v1/admin/responses?limit=10" \
  -H "Authorization: Bearer $TOKEN"

curl http://localhost:8000/api/v1/admin/insights \
  -H "Authorization: Bearer $TOKEN"

curl http://localhost:8000/api/v1/admin/export \
  -H "Authorization: Bearer $TOKEN" \
  -o responses.csv
```

---

## Deploy later

Typical flow (Railway, Render, Fly, etc.):

1. Set environment variables in the platform dashboard
2. Point `DATABASE_URL` at a managed PostgreSQL instance
3. Set `FRONTEND_ORIGIN` to your production frontend URL (e.g. `https://your-app.vercel.app`)
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Update the frontend `js/api.js` → `BASE_URL` to the production API URL

---

## Security notes

- Passwords are bcrypt-hashed
- Admin routes require valid JWT
- CORS restricted to `FRONTEND_ORIGIN`
- Pydantic validates all input
- Errors do not leak stack traces or secrets
- Response codes are sequential public identifiers, not DB primary keys

This is a small research platform with sensible production basics.

---

© 2026 IGRIS Technologies
# Igris-buisiness-pulse-api
