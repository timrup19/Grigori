# Claude Code Instructions - Prozorro Sentinel

## Project Overview

You're building a **Procurement Risk Explorer** for Ukraine - a public-facing web app that analyzes government contracts and flags potential corruption risks. Think of it like a "credit score" for government contractors.

**Live demo target:** Something journalists and civil society can use to find investigation leads.

## What's Already Built

### Backend (FastAPI + PostgreSQL) - ~80% complete
- ✅ Database schema (`backend/schema.sql`)
- ✅ FastAPI app structure with all routers
- ✅ Pydantic schemas for all endpoints
- ✅ Risk scoring engine (ported from working Colab prototype)
- ✅ Network analyzer for co-bidding graphs
- ✅ Prozorro API client
- 🔲 SQLAlchemy models (need to create from schema)
- 🔲 Actual database queries in API routes (currently placeholders)
- 🔲 Alembic migrations
- 🔲 Docker configuration

### Frontend (React + Vite + Tailwind) - ~30% complete
- ✅ Project setup (Vite, Tailwind, routing)
- ✅ API service client
- ✅ Layout with header/nav
- ✅ Base CSS with risk badges, cards, etc.
- 🔲 All page components (Home, Search, Alerts, Network, Map, About)
- 🔲 Shared components (RiskBadge, SearchBar, AlertCard, etc.)
- 🔲 Network graph visualization (use vis-network)
- 🔲 Ukraine risk heatmap (use react-simple-maps)

## Core Features to Build

### 1. Contract Risk Lookup (Search Page)
- Search bar with autocomplete
- Filter by region, risk level, value range
- Results show: contractor name, EDRPOU, risk score badge, win count, total value
- Click to see contractor detail page

### 2. Red Flag Feed (Alerts Page)
- Live feed of high-risk contracts from past 7 days
- Each card shows: tender title, value, buyer, winner, risk score, reasons
- Filter by region, risk category
- Stats summary at top (total alerts, value at risk)

### 3. Network Visualization (Network Page)
- Search for a contractor → see their co-bidding network
- Interactive graph (vis-network): nodes = companies, edges = co-bidding frequency
- Node color by risk score
- Click node to see details
- Highlight suspicious clusters

### 4. Regional Risk Heatmap (Map Page)
- Ukraine map colored by average risk score
- Click region to see details panel
- Show top flagged contracts in each region

## Tech Stack

```
Backend:
- FastAPI
- PostgreSQL 15+ (with pg_trgm for fuzzy search)
- SQLAlchemy 2.0 (async)
- Redis (optional, for caching)

Frontend:
- React 18
- Vite
- TailwindCSS
- vis-network (network graphs)
- react-simple-maps (Ukraine map)
- Recharts (charts)
- Axios

Deploy:
- Railway (backend + Postgres)
- Vercel (frontend)
```

## Priority Order

1. **Get backend running with real data**
   - Create SQLAlchemy models from schema.sql
   - Implement database queries in API routes
   - Create sync script to pull from Prozorro API
   - Seed with ~1000 tenders for demo

2. **Build Search page** (most important feature)
   - SearchBar component with debounced input
   - Results table with pagination
   - RiskBadge component
   - ContractorCard component

3. **Build Alerts page** (the "wow" feature)
   - AlertFeed component
   - AlertCard with risk reasons
   - Real-time feel (auto-refresh)

4. **Build Network page** (the "holy shit" feature)
   - NetworkGraph component using vis-network
   - Search contractor → load subgraph
   - Node click → show details

5. **Build Map page**
   - Ukraine regions GeoJSON
   - Color by risk score
   - Click for region details

## File Structure Reference

```
prozorro-sentinel/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry (done)
│   │   ├── config.py        # Settings (done)
│   │   ├── database.py      # DB connection (done)
│   │   ├── schemas.py       # Pydantic models (done)
│   │   ├── models/          # SQLAlchemy models (TODO)
│   │   ├── api/             # Route handlers (placeholder logic)
│   │   └── services/        # Business logic (done)
│   ├── scripts/
│   │   ├── sync_prozorro.py # Data sync (TODO)
│   │   └── seed_demo.py     # Demo data (TODO)
│   └── schema.sql           # DB schema (done)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/      # Layout (done)
│   │   │   ├── shared/      # RiskBadge, StatCard, etc. (TODO)
│   │   │   ├── search/      # SearchBar, Results (TODO)
│   │   │   ├── alerts/      # AlertFeed, AlertCard (TODO)
│   │   │   ├── network/     # NetworkGraph (TODO)
│   │   │   └── map/         # RiskHeatmap (TODO)
│   │   ├── pages/           # Page components (TODO)
│   │   ├── services/api.js  # API client (done)
│   │   └── App.jsx          # Routing (done)
```

## Quick Start Commands

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env with DATABASE_URL
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Key API Endpoints

| Feature | Endpoint | Purpose |
|---------|----------|---------|
| Search | `GET /api/search/contractors?q=` | Find companies |
| Alerts | `GET /api/alerts?days=7` | Red flag feed |
| Network | `GET /api/network/{id}` | Co-bidding graph |
| Regions | `GET /api/regions` | Heatmap data |
| Stats | `GET /api/stats/overview` | Dashboard metrics |

## Risk Scoring (Already Implemented)

Score 0-100 based on:
- Price anomaly (30%) - Z-score + Isolation Forest
- Bid patterns (25%) - Low CV suggests collusion
- Single bidder (20%) - No competition flag
- Network risk (15%) - Centrality in co-bidding graph
- High value (10%) - Top 10% contract value

Categories: Low (0-25), Medium (26-50), High (51-75), Critical (76-100)

## Demo Data Strategy

For the MVP, sync ~1000 recent tenders from Prozorro API:
1. Fetch tender list from `https://public-api.prozorro.gov.ua/api/2.5/tenders`
2. Get details for each tender
3. Parse and store in PostgreSQL
4. Run risk scoring engine
5. Build co-bidding network

## Design Notes

- Use Ukrainian region names in Cyrillic
- Risk colors: green/yellow/orange/red
- Keep it professional but accessible
- Mobile-responsive
- No auth needed (public demo)

## Questions? Check These Files

- `README.md` - Full architecture overview
- `backend/schema.sql` - Database structure
- `backend/app/schemas.py` - All data types
- `backend/app/services/risk_engine.py` - Scoring logic
- `frontend/src/services/api.js` - All API calls

---

**Goal:** Get this to a state where a journalist can search a contractor name, see their risk score, explore their network, and find potential investigation leads. Make it polished enough to demo to donors and YC.
