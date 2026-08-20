<h1 align="center">
  <img src="https://img.shields.io/badge/MetGo-AI%20Induction%20Planning-0ea5e9?style=for-the-badge" alt="MetGo" />
</h1>

<p align="center">
  <strong>AI-powered overnight train induction planning dashboard for Kochi Metro Rail Limited (KMRL)</strong><br/>
  Built as a decision-support tool — the system recommends; the operator decides.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-TimescaleDB-336791?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Celery-async%20solver-37814A?logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

---

## Overview

**MetGo** is a real-time, AI-assisted induction planning system that automates the overnight assignment of Kochi Metro's fleet of 25 trains to service, maintenance, cleaning, standby, or breakdown states — optimizing for constraints like fitness certificates, job cards, and bay availability.

It features:
- 🚆 **AI Solver (Lockwood)** — Constraint-based OR-Tools optimizer for overnight fleet scheduling
- 📊 **Live Dashboard** — Real-time fleet status, alerts, and plan overview
- 🧠 **Explainability Engine** — Human-readable justifications for every assignment decision
- 🔬 **What-If Simulator** — Simulate breakdowns and overrides, see how the plan adapts
- 🏗️ **Digital Twin** — Animated live view of Muttom Yard bay assignments
- 🗺️ **Induction Plan View** — Full breakdown of every train's assigned state

---

## Project Structure

```
MetGo/
├── kmrl-backend/       # FastAPI + Celery backend (Python)
│   ├── app/            # Core application modules
│   │   ├── routers/    # API endpoints (plan, trains, health)
│   │   ├── models/     # SQLAlchemy DB models
│   │   ├── services/   # Explainability engine, business logic
│   │   └── worker/     # Celery async tasks (plan generation)
│   ├── alembic/        # Database migrations
│   └── requirements.txt
├── kmrl-frontend/      # React + Vite frontend
│   └── src/
│       ├── App.jsx     # Main application & all views
│       ├── App.css     # Design system & component styles
│       ├── Landing.jsx # Landing page
│       └── api.js      # API client
└── LOCKWOOD/           # Lockwood OR-Tools optimizer module
    └── src/solver/     # Core constraint solver
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (TimescaleDB recommended)
- Redis
- (Optional) Neo4j Community Edition

### Backend Setup

```bash
cd kmrl-backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your local database credentials

# Run database migrations
alembic upgrade head

# Seed the database
python -m app.seed.main

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000

# In a separate terminal, start the Celery worker
celery -A app.worker.celery_app worker --loglevel=info
```

### Frontend Setup

```bash
cd kmrl-frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The dashboard will be available at **http://localhost:3000**

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Backend health check |
| `POST` | `/plan/generate` | Generate a new overnight induction plan |
| `POST` | `/plan/what-if` | Re-run solver with a manual override |
| `GET` | `/plan/{plan_id}/explain/{train_id}` | Get explainability for a train's assignment |
| `GET` | `/trains/` | List all trains with summary data |
| `GET` | `/trains/{train_id}` | Get detailed data for a single train |

---

## Environment Variables

Copy `kmrl-backend/.env.example` to `kmrl-backend/.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://kmrl:kmrl_secret@localhost:5432/kmrl_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `SECRET_KEY` | App secret key | **Change in production!** |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite, Framer Motion, Lucide |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Solver | Google OR-Tools (via Lockwood module) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL / TimescaleDB |
| Graph DB | Neo4j (optional) |
| Styling | Vanilla CSS with custom design system |

---

## Key Concepts

- **Induction Plan** — The overnight assignment of every train to a duty state for the next service day
- **Lockwood Solver** — The internal OR-Tools constraint optimizer. Do not rename any internal functions or module paths.
- **Fitness Certificate** — A regulatory compliance certificate per train with an expiry date. Expired trains cannot enter service (hard constraint).
- **What-If Scenario** — A simulation where an operator forces one train into a specific state (e.g., breakdown) to see how the solver adapts the rest of the fleet.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

> Built with ❤️ for KMRL operations. This system is a decision-support tool — trained professionals make the final call.
