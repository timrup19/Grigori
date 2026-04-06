# Grigori — Beneficial Ownership Graph: Implementation Plan

> **Scope:** Integrate free public APIs to build a proprietary entity intelligence layer on top of Prozorro data.
> **APIs:** OpenSanctions · NAZK E-Declarations · Ukrainian EDR · GLEIF
> **Phases:** 4 backend phases + 1 frontend phase

---

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Phase 1 — OpenSanctions Integration
**Goal:** Flag any Prozorro contractor that is sanctioned or politically exposed.
**New alert type:** `SANCTIONED_ENTITY_CONTRACT`
**Estimated new files:** 3 backend, 1 frontend component

---

### 1.1 Database Changes

- [x] Add columns to `contractors` table:
  ```sql
  is_sanctioned        BOOLEAN DEFAULT FALSE
  is_pep               BOOLEAN DEFAULT FALSE
  sanctions_hits       JSONB   DEFAULT '[]'   -- raw OpenSanctions match results
  enriched_at          TIMESTAMP WITH TIME ZONE
  ```
- [x] Create Alembic migration: `alembic/versions/002_add_sanctions_fields.py`
- [ ] Run migration against local DB — run manually:
  ```bash
  docker exec sentinel-db psql -U postgres -d prozorro_sentinel -c "
  ALTER TABLE contractors ADD COLUMN IF NOT EXISTS is_sanctioned BOOLEAN DEFAULT FALSE;
  ALTER TABLE contractors ADD COLUMN IF NOT EXISTS is_pep BOOLEAN DEFAULT FALSE;
  ALTER TABLE contractors ADD COLUMN IF NOT EXISTS sanctions_hits JSONB DEFAULT '[]'::jsonb;
  ALTER TABLE contractors ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMP WITH TIME ZONE;
  CREATE INDEX IF NOT EXISTS idx_contractors_is_sanctioned ON contractors (is_sanctioned) WHERE is_sanctioned = true;
  CREATE INDEX IF NOT EXISTS idx_contractors_is_pep ON contractors (is_pep) WHERE is_pep = true;
  INSERT INTO alembic_version (version_num) VALUES ('002') ON CONFLICT DO NOTHING;
  "
  ```

---

### 1.2 Backend — OpenSanctions Client

**New file:** `backend/app/services/opensanctions_client.py`

- [x] `OpenSanctionsClient` class with `httpx.AsyncClient`
- [x] Method: `match_batch(entities: list[dict]) -> dict` — batch match up to 50 entities per request
- [x] Parse response: extract score, `is_pep` flag, datasets, properties
- [x] Handle rate limits: catch HTTP 429, wait `Retry-After` seconds
- [x] Config: `OPENSANCTIONS_API_KEY`, `OPENSANCTIONS_MIN_SCORE` in `config.py`

---

### 1.3 Backend — Enrichment Service

**New file:** `backend/app/services/enrichment_service.py`

- [x] `EnrichmentService` class orchestrating all enrichment sources
- [x] `enrich_batch()` — chunks contractors into 50-entity batches, calls OpenSanctions
- [x] Updates `is_sanctioned`, `is_pep`, `sanctions_hits`, `enriched_at` on contractor record
- [x] Creates `sanctioned_entity` alert (risk_score=100, category=critical) on hit

---

### 1.4 Backend — Hook into Sync Pipeline

**File:** `backend/scripts/sync_prozorro.py`

- [x] Import `EnrichmentService`
- [x] Step 11: `_enrich_contractors()` runs after `_create_alerts()`
- [x] Queries contractors where `enriched_at IS NULL` (up to 500 per sync run)
- [x] `sanctions_hits` and `pep_hits` added to sync stats

---

### 1.5 Backend — New Alert Type

- [x] `SANCTIONED_ENTITY = "sanctioned_entity"` added to `AlertType` enum in `schemas.py`
- [x] Alert created in `enrichment_service._create_sanctions_alert()` with risk_score=100

---

### 1.6 Backend — API Endpoint

- [x] `GET /api/contractors/{id}/enrichment` added to `contractors.py`
- [x] `ContractorEnrichment` response schema added to `schemas.py`
- [x] `ContractorDetail` schema updated with `is_sanctioned`, `is_pep`, `enriched_at` fields

---

### 1.7 Frontend — Sanctions Badge on Contractor Profile

- [x] `contractorsAPI.getEnrichment(id)` added to `services/api.js`
- [x] Red banner if `is_sanctioned = true` with list names and match scores
- [x] Orange banner if `is_pep = true` with PEP dataset sources
- [x] Enrichment timestamp shown at bottom of header card

---

### Phase 1 Completion Criteria
- [ ] Migration applied to DB (run SQL command above)
- [x] OpenSanctions client, enrichment service, sync hook all implemented
- [x] `sanctioned_entity` alert type wired up end-to-end
- [x] Frontend banners live on contractor profile page
- After running sync: any sanctioned contractor gets flagged and alert appears in feed

---
---

## Phase 2 — Ukrainian EDR (Company Registry)
**Goal:** Attach real director/founder names to every contractor EDRPOU. Feed these names into later phases (NAZK cross-reference).
**API:** `https://api-sandbox.openprocurement.org/api/1.0/verify?id={EDRPOU}`
**New alert type:** `DIRECTOR_IS_PEP`

---

### 2.1 Database Changes

- [ ] Create new table `contractor_directors`:
  ```sql
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  contractor_id   UUID REFERENCES contractors(id) ON DELETE CASCADE
  full_name       TEXT NOT NULL
  role            TEXT  -- "director", "founder", "beneficial_owner"
  edrpou_person   TEXT  -- personal tax ID if available
  source          TEXT DEFAULT 'edr'
  fetched_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  ```
- [ ] Create Alembic migration: `alembic revision --autogenerate -m "add_contractor_directors"`
- [ ] Run migration

---

### 2.2 Backend — EDR Client

**New file:** `backend/app/services/edr_client.py`

- [ ] `EDRClient` class
- [ ] Method: `get_company(edrpou: str) -> dict | None`
  - GET `https://api-sandbox.openprocurement.org/api/1.0/verify?id={edrpou}`
  - Basic auth (check if needed for production endpoint vs sandbox)
- [ ] Parse response: extract `legalName`, `registrationStatus`, director names from nested fields
- [ ] Return structured dict: `{ name, status, directors: [{ full_name, role }] }`
- [ ] Handle 404 (company not found), 429 (rate limit), network errors

---

### 2.3 Backend — Integrate into EnrichmentService

**File:** `backend/app/services/enrichment_service.py`

- [ ] Add `EDRClient` import
- [ ] In `enrich_contractor()`: after OpenSanctions check, call `EDRClient.get_company(contractor.edrpou)`
- [ ] Upsert directors into `contractor_directors` table (on conflict on `contractor_id + full_name`, update `role`)
- [ ] Add `edr_status` field to contractor: `active | dissolved | unknown` — dissolved company winning active contracts is a risk signal

---

### 2.4 Backend — API Endpoint

**File:** `backend/app/api/contractors.py`

- [ ] Extend `GET /api/contractors/{id}/enrichment` to include:
  ```json
  {
    "directors": [{ "full_name": "...", "role": "director" }],
    "edr_status": "active"
  }
  ```

---

### 2.5 Frontend — Directors Panel on Contractor Profile

**File:** `frontend/src/pages/ContractorDetail.jsx`

- [ ] Add "Company Officers" section listing directors and founders
- [ ] Each director name becomes a clickable search — links to `/search?q={name}` to find other companies they appear in
- [ ] If `edr_status = dissolved`: show warning badge "Company may be dissolved"

---

### Phase 2 Completion Criteria
- `contractor_directors` table populated for all synced contractors
- Director names visible on contractor profile pages
- Director name search works across the platform

---
---

## Phase 3 — NAZK E-Declarations (Conflict of Interest Detection)
**Goal:** Cross-reference Prozorro procurement officials (buyers) with contractor directors to detect conflicts of interest.
**API:** `https://public-api.nazk.gov.ua/v2/documents/list`
**New alert type:** `CONFLICT_OF_INTEREST`
**This is the uniquely Ukrainian moat feature.**

---

### 3.1 Database Changes

- [ ] Create new table `nazk_declarations`:
  ```sql
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  declarant_name    TEXT NOT NULL
  declarant_post    TEXT
  declaration_year  INTEGER
  declaration_type  TEXT
  agency_name       TEXT  -- which ministry/agency they work for
  declared_companies JSONB DEFAULT '[]'  -- companies they declared ownership in
  raw_data          JSONB
  fetched_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  ```
- [ ] Create new table `conflict_flags`:
  ```sql
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
  tender_id       UUID REFERENCES tenders(id)
  contractor_id   UUID REFERENCES contractors(id)
  buyer_id        UUID REFERENCES buyers(id)
  official_name   TEXT   -- the procurement official
  director_name   TEXT   -- the contractor director
  match_type      TEXT   -- "same_person" | "family_name_match" | "declared_company"
  confidence      FLOAT
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  ```
- [ ] Create Alembic migration: `alembic revision --autogenerate -m "add_nazk_conflict_tables"`
- [ ] Run migration

---

### 3.2 Backend — NAZK Client

**New file:** `backend/app/services/nazk_client.py`

- [ ] `NAZKClient` class
- [ ] Method: `search_declarations(name: str, year: int = None) -> list[dict]`
  - GET `https://public-api.nazk.gov.ua/v2/documents/list?query={name}`
  - Paginate through results (pages 1–100 max per API)
- [ ] Method: `get_declaration(document_id: str) -> dict`
  - GET `https://public-api.nazk.gov.ua/v2/documents/{document_id}`
- [ ] Parse: extract declarant name, agency, declared companies/assets
- [ ] Cache results locally (NAZK data doesn't change often) — store in `nazk_declarations` table

---

### 3.3 Backend — Conflict Detection Logic

**New file:** `backend/app/services/conflict_detector.py`

- [ ] `ConflictDetector` class
- [ ] Method: `check_tender(tender_id: UUID, db: AsyncSession) -> list[dict]`
  1. Load tender + buyer agency name + contractor directors
  2. For each director name: query `nazk_declarations` for declarations where `agency_name` matches the buyer's agency
  3. Fuzzy name match (use `rapidfuzz` library — already likely in requirements or easy to add): flag if director name matches a declaration from that agency with score > 85
  4. Insert into `conflict_flags` table
  5. If any flags found: create `CONFLICT_OF_INTEREST` alert at `risk_score = 95`
- [ ] Schedule this check to run after each sync for all newly imported tenders

---

### 3.4 Backend — API Endpoint

**File:** `backend/app/api/contractors.py` or new `backend/app/api/intelligence.py`

- [ ] `GET /api/tenders/{id}/conflicts` — returns conflict flags for a tender
- [ ] `GET /api/contractors/{id}/conflicts` — returns all conflict flags involving this contractor

---

### 3.5 Frontend — Conflict of Interest Panel

- [ ] New `ConflictAlert` component in `frontend/src/components/alerts/`
- [ ] Show on tender detail page (when built) and contractor profile page
- [ ] Display: official name, their agency, contractor director, match confidence
- [ ] Link to the public NAZK declaration: `https://public.nazk.gov.ua/documents/{id}`

---

### Phase 3 Completion Criteria
- NAZK declarations searchable and cached in DB
- Conflict detection runs on every synced tender
- `CONFLICT_OF_INTEREST` alerts appear in the main alert feed
- Alert links to the actual NAZK declaration for verification

---
---

## Phase 4 — GLEIF International Entity Enrichment
**Goal:** For contractors that are subsidiaries of international companies, expose the parent entity and flag if the parent is sanctioned or Russian state-owned.
**API:** `https://api.gleif.org/api/v1/lei-records`
**Free, 60 req/min, no key needed.**

---

### 4.1 Database Changes

- [ ] Add columns to `contractors` table:
  ```sql
  lei_code           TEXT   -- Legal Entity Identifier
  parent_lei_code    TEXT
  parent_name        TEXT
  ultimate_parent_name TEXT
  gleif_enriched_at  TIMESTAMP WITH TIME ZONE
  ```
- [ ] Create Alembic migration: `alembic revision --autogenerate -m "add_gleif_fields_to_contractors"`
- [ ] Run migration

---

### 4.2 Backend — GLEIF Client

**New file:** `backend/app/services/gleif_client.py`

- [ ] `GLEIFClient` class (no auth needed)
- [ ] Method: `search_by_name(name: str) -> list[dict]`
  - GET `https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]={name}`
  - Returns list of matching LEI records
- [ ] Method: `get_by_lei(lei: str) -> dict`
  - GET `https://api.gleif.org/api/v1/lei-records/{lei}`
- [ ] Method: `get_parent(lei: str) -> dict | None`
  - GET `https://api.gleif.org/api/v1/lei-records/{lei}/direct-parent`
- [ ] Method: `get_ultimate_parent(lei: str) -> dict | None`
  - GET `https://api.gleif.org/api/v1/lei-records/{lei}/ultimate-parent`
- [ ] Rate limit: 60 req/min — add `asyncio.sleep(1.1)` between calls or use a semaphore

---

### 4.3 Backend — Integrate into EnrichmentService

**File:** `backend/app/services/enrichment_service.py`

- [ ] In `enrich_contractor()`: fuzzy match contractor name against GLEIF
- [ ] If match found (score > 90): populate `lei_code`, then fetch parent chain
- [ ] Flag contractors whose `ultimate_parent_name` contains known Russian state entity keywords (`"Сбербанк"`, `"Газпром"`, `"Роснефть"`, `"ВТБ"`, etc.)
- [ ] Cross-check parent LEI against OpenSanctions (already integrated from Phase 1)

---

### 4.4 Frontend — Parent Structure on Contractor Profile

**File:** `frontend/src/pages/ContractorDetail.jsx`

- [ ] If `lei_code` present: add "Corporate Structure" section
- [ ] Show: `Subsidiary of → {parent_name} → Ultimate parent: {ultimate_parent_name}`
- [ ] If ultimate parent is Russian state entity: red warning banner

---

### Phase 4 Completion Criteria
- International contractors enriched with LEI and parent chain
- Russian state-owned subsidiaries flagged automatically
- Parent structure visible on contractor profile

---
---

## Phase 5 — Frontend: Intelligence Dashboard
**Goal:** Surface all enrichment data in a unified "Entity Intelligence" view.

---

### 5.1 Contractor Profile Enhancements

- [ ] **Sanctions strip** (Phase 1): red/orange banner at top if sanctioned or PEP-linked
- [ ] **Company Officers panel** (Phase 2): directors list with search links
- [ ] **Conflict of Interest panel** (Phase 3): official-director overlap alerts with NAZK links
- [ ] **Corporate Structure panel** (Phase 4): parent chain visualization
- [ ] **Enrichment metadata footer**: "Last enriched: {date} · Sources: OpenSanctions, EDR, GLEIF"

---

### 5.2 New: Entity Intelligence Page

**New file:** `frontend/src/pages/EntityIntelligence.jsx`
**Route:** `/intelligence`

- [ ] Search any name, EDRPOU, or LEI
- [ ] Returns: all contractors matching, their sanctions status, directors, declared assets, parent chain
- [ ] This is the "investigator's workbench" view

---

### 5.3 Alert Feed Enhancements

**File:** `frontend/src/components/alerts/AlertCard.jsx`

- [ ] New visual treatment for `SANCTIONED_ENTITY_CONTRACT` — red, highest severity
- [ ] New visual treatment for `CONFLICT_OF_INTEREST` — purple (suggests corruption, not just risk)
- [ ] Link from alert directly to NAZK declaration or OpenSanctions entity page

---

### 5.4 Home Page Stats

**File:** `frontend/src/pages/Home.jsx`

- [ ] Add stat: "Sanctioned entities detected: {n}"
- [ ] Add stat: "Conflicts of interest flagged: {n}"

---

### Phase 5 Completion Criteria
- Intelligence data visible to users without needing to check raw DB
- Entity Intelligence page usable as an investigator tool
- Sanctions and conflict alerts styled distinctly in the alert feed

---
---

## Dependency Order

```
Phase 1 (OpenSanctions)        ← start here, no dependencies
    ↓
Phase 2 (EDR Directors)        ← needs contractor table from Phase 1 migration
    ↓
Phase 3 (NAZK Conflicts)       ← needs director names from Phase 2
    ↓
Phase 4 (GLEIF Parents)        ← can run parallel to Phase 3
    ↓
Phase 5 (Frontend)             ← needs all backend phases complete
```

---

## New Files Summary

| File | Phase | Purpose |
|---|---|---|
| `backend/app/services/opensanctions_client.py` | 1 | OpenSanctions API client |
| `backend/app/services/enrichment_service.py` | 1 | Orchestrates all enrichment |
| `backend/app/services/edr_client.py` | 2 | Ukrainian company registry client |
| `backend/app/services/nazk_client.py` | 3 | NAZK declarations API client |
| `backend/app/services/conflict_detector.py` | 3 | Conflict of interest detection logic |
| `backend/app/services/gleif_client.py` | 4 | GLEIF LEI API client |
| `backend/app/api/intelligence.py` | 3–4 | New `/api/intelligence` router |
| `frontend/src/pages/EntityIntelligence.jsx` | 5 | Investigator workbench page |
| `frontend/src/components/alerts/ConflictAlert.jsx` | 5 | COI alert component |
| `alembic/versions/*_sanctions_fields.py` | 1 | Migration: sanctions columns |
| `alembic/versions/*_contractor_directors.py` | 2 | Migration: directors table |
| `alembic/versions/*_nazk_conflict_tables.py` | 3 | Migration: declarations + conflicts |
| `alembic/versions/*_gleif_fields.py` | 4 | Migration: LEI columns |

---

## Paid Tier Upgrades (Post-Traction)

Track here for when the time comes:

- [ ] **Opendatabot** — replaces EDR client with full multi-registry Ukrainian data in one call
- [ ] **OpenCorporates** — global company registry, upgrade from GLEIF for entity resolution
- [ ] **YouControl API** — Ukrainian market leader for company intelligence, beneficial ownership
- [ ] **OpenSanctions commercial** — upgrade from free tier, enables commercial use at €0.10/call
- [ ] **Sayari Analytics** — enterprise beneficial ownership graph (competitor reference point for positioning)

---

*Last updated: 2026-04-06*
