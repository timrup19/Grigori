# Prozorro Sentinel - Public Risk Explorer

**Procurement risk intelligence for Ukraine's reconstruction**

A public-facing web application that lets anyone explore Ukrainian procurement data and see real-time risk signals. Built to demonstrate predictive capital risk intelligence.

## 🎯 What This Does

1. **Contract Risk Lookup** - Search any contractor, buyer, or tender and see risk scores
2. **Red Flag Feed** - Live feed of highest-risk contracts from the past 48 hours
3. **Network Visualization** - See hidden connections between companies
4. **Regional Heatmap** - Geographic view of where risk concentrates

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    (React + TailwindCSS)                        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  Search   │ │ Red Flag  │ │  Network  │ │  Heatmap  │       │
│  │  & Lookup │ │   Feed    │ │   Graph   │ │    Map    │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND API                               │
│                    (FastAPI + Python)                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ /search   │ │ /alerts   │ │ /network  │ │ /regions  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────┐     │
│  │              RISK SCORING ENGINE                       │     │
│  │  • Price Anomaly Detection (Isolation Forest + Z-score)│     │
│  │  • Bid Pattern Analysis (CV, single-bidder flags)      │     │
│  │  • Network Analysis (co-bidding graphs, communities)   │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────────────────────┐     │
│  │ PostgreSQL│ │   Redis   │ │   Prozorro API (source)   │     │
│  │ (primary) │ │  (cache)  │ │   Nightly sync job        │     │
│  └───────────┘ └───────────┘ └───────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
prozorro-sentinel/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Database connection & session
│   │   │
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── tender.py
│   │   │   ├── contractor.py
│   │   │   └── risk_score.py
│   │   │
│   │   ├── schemas/             # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── tender.py
│   │   │   ├── contractor.py
│   │   │   ├── risk.py
│   │   │   └── network.py
│   │   │
│   │   ├── api/                 # API routes
│   │   │   ├── __init__.py
│   │   │   ├── search.py        # /api/search endpoints
│   │   │   ├── alerts.py        # /api/alerts endpoints
│   │   │   ├── network.py       # /api/network endpoints
│   │   │   ├── regions.py       # /api/regions endpoints
│   │   │   └── stats.py         # /api/stats endpoints
│   │   │
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── prozorro_client.py    # Prozorro API client
│   │   │   ├── risk_engine.py        # Risk scoring algorithms
│   │   │   ├── network_analyzer.py   # Network/graph analysis
│   │   │   └── sync_service.py       # Data synchronization
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   │
│   ├── scripts/
│   │   ├── sync_prozorro.py     # Cron job for data sync
│   │   └── seed_demo_data.py    # Generate demo data
│   │
│   ├── tests/
│   │   └── ...
│   │
│   ├── alembic/                 # Database migrations
│   │   └── ...
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Footer.jsx
│   │   │   │   └── Layout.jsx
│   │   │   │
│   │   │   ├── search/
│   │   │   │   ├── SearchBar.jsx
│   │   │   │   ├── SearchResults.jsx
│   │   │   │   └── ContractorCard.jsx
│   │   │   │
│   │   │   ├── alerts/
│   │   │   │   ├── AlertFeed.jsx
│   │   │   │   └── AlertCard.jsx
│   │   │   │
│   │   │   ├── network/
│   │   │   │   ├── NetworkGraph.jsx
│   │   │   │   └── NetworkControls.jsx
│   │   │   │
│   │   │   ├── map/
│   │   │   │   ├── RiskHeatmap.jsx
│   │   │   │   └── RegionPopup.jsx
│   │   │   │
│   │   │   └── shared/
│   │   │       ├── RiskBadge.jsx
│   │   │       ├── StatCard.jsx
│   │   │       └── LoadingSpinner.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Search.jsx
│   │   │   ├── Alerts.jsx
│   │   │   ├── Network.jsx
│   │   │   ├── Map.jsx
│   │   │   └── About.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useSearch.js
│   │   │   ├── useAlerts.js
│   │   │   └── useNetwork.js
│   │   │
│   │   ├── services/
│   │   │   └── api.js           # API client
│   │   │
│   │   ├── utils/
│   │   │   ├── formatters.js
│   │   │   └── constants.js
│   │   │
│   │   ├── App.jsx
│   │   ├── index.jsx
│   │   └── index.css
│   │
│   ├── public/
│   │   └── index.html
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis (optional, for caching)

### Local Development

1. **Clone and setup backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database credentials
```

2. **Initialize database:**
```bash
alembic upgrade head
python scripts/seed_demo_data.py  # Optional: load demo data
```

3. **Run backend:**
```bash
uvicorn app.main:app --reload --port 8000
```

4. **Setup frontend:**
```bash
cd frontend
npm install
cp .env.example .env
```

5. **Run frontend:**
```bash
npm run dev
```

6. **Access the app:**
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Docker (Production-like)

```bash
docker-compose up --build
```

## 📊 API Endpoints

### Search
- `GET /api/search/contractors?q={query}` - Search contractors by name
- `GET /api/search/tenders?q={query}` - Search tenders
- `GET /api/search/buyers?q={query}` - Search government buyers

### Contractor Details
- `GET /api/contractors/{id}` - Get contractor profile with risk score
- `GET /api/contractors/{id}/tenders` - Get contractor's tender history
- `GET /api/contractors/{id}/network` - Get contractor's network connections

### Alerts (Red Flags)
- `GET /api/alerts?days={n}` - Get high-risk contracts from last N days
- `GET /api/alerts/stats` - Get alert statistics

### Network Analysis
- `GET /api/network/{contractor_id}` - Get network graph for contractor
- `GET /api/network/communities` - Get detected suspicious communities

### Regional Data
- `GET /api/regions` - Get all regions with risk summaries
- `GET /api/regions/{region_id}/tenders` - Get tenders for a region

### Statistics
- `GET /api/stats/overview` - Platform-wide statistics
- `GET /api/stats/risk-distribution` - Risk score distribution

## 🧮 Risk Scoring

Each tender/contractor receives a composite risk score (0-100) based on:

| Signal | Weight | Description |
|--------|--------|-------------|
| Price Anomaly | 30% | Deviation from category median, Isolation Forest |
| Bid Pattern | 25% | Coefficient of variation, bid clustering |
| Single Bidder | 20% | Lack of competition flag |
| Network Risk | 15% | Centrality in co-bidding network |
| High Value | 10% | Top decile contract value |

### Risk Categories
- **Low (0-25):** Normal patterns
- **Medium (26-50):** Minor anomalies, worth monitoring
- **High (51-75):** Multiple red flags, needs review
- **Critical (76-100):** Strong corruption indicators

## 🔄 Data Sync

The system syncs with Prozorro API nightly:

```bash
# Manual sync
python scripts/sync_prozorro.py

# Or via cron (add to crontab)
0 2 * * * /path/to/venv/bin/python /path/to/scripts/sync_prozorro.py
```

## 🛠️ Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (primary database)
- Redis (caching, optional)
- Alembic (migrations)
- scikit-learn (ML models)
- NetworkX (graph analysis)

**Frontend:**
- React 18
- Vite (build tool)
- TailwindCSS (styling)
- React Router (navigation)
- Recharts (charts)
- vis.js (network visualization)
- react-simple-maps (Ukraine map)
- Axios (API client)

**Infrastructure:**
- Docker + Docker Compose
- Railway / Render (backend hosting)
- Vercel (frontend hosting)

## 📈 Future Enhancements

- [ ] Satellite imagery verification integration
- [ ] Real-time WebSocket alerts
- [ ] Export reports as PDF
- [ ] API access for journalists
- [ ] Ukrainian language support
- [ ] Saved searches / watchlists
- [ ] Email alerts for specific contractors

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

This is an open-source project aimed at improving procurement transparency. Contributions welcome!

---

**Built by [Prozorro Sentinel Team](https://prozorro-sentinel.com)**
