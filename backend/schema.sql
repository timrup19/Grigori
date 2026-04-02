-- Grigori Database Schema
-- PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Contractors (bidders/suppliers)
CREATE TABLE contractors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    edrpou VARCHAR(20) UNIQUE NOT NULL,  -- Ukrainian company registration number
    name VARCHAR(500) NOT NULL,
    name_normalized VARCHAR(500),  -- Lowercase, no punctuation for matching
    
    -- Address info
    address TEXT,
    region VARCHAR(100),
    postal_code VARCHAR(20),
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    
    -- Aggregated stats (updated by triggers/jobs)
    total_tenders INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_value_won DECIMAL(20, 2) DEFAULT 0,
    win_rate DECIMAL(5, 4),
    
    -- Risk scoring
    risk_score DECIMAL(5, 2),
    risk_category VARCHAR(20),  -- 'low', 'medium', 'high', 'critical'
    risk_updated_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for contractor search
CREATE INDEX idx_contractors_edrpou ON contractors(edrpou);
CREATE INDEX idx_contractors_name_trgm ON contractors USING gin(name_normalized gin_trgm_ops);
CREATE INDEX idx_contractors_region ON contractors(region);
CREATE INDEX idx_contractors_risk ON contractors(risk_score DESC);
CREATE INDEX idx_contractors_risk_category ON contractors(risk_category);

-- ============================================================================

-- Buyers (procuring entities / government bodies)
CREATE TABLE buyers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prozorro_id VARCHAR(100) UNIQUE,  -- ID from Prozorro
    edrpou VARCHAR(20),
    name VARCHAR(500) NOT NULL,
    name_normalized VARCHAR(500),
    
    -- Location
    region VARCHAR(100),
    address TEXT,
    
    -- Classification
    buyer_type VARCHAR(50),  -- 'central', 'regional', 'local', 'enterprise'
    
    -- Stats
    total_tenders INTEGER DEFAULT 0,
    total_value DECIMAL(20, 2) DEFAULT 0,
    avg_competition DECIMAL(5, 2),  -- Average bids per tender
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_buyers_prozorro_id ON buyers(prozorro_id);
CREATE INDEX idx_buyers_name_trgm ON buyers USING gin(name_normalized gin_trgm_ops);
CREATE INDEX idx_buyers_region ON buyers(region);

-- ============================================================================

-- Tenders
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prozorro_id VARCHAR(100) UNIQUE NOT NULL,  -- Tender ID from Prozorro
    
    -- Basic info
    title TEXT,
    description TEXT,
    status VARCHAR(50),  -- 'active', 'complete', 'cancelled', 'unsuccessful'
    procurement_method VARCHAR(50),
    procurement_method_type VARCHAR(100),
    
    -- Value
    expected_value DECIMAL(20, 2),
    currency VARCHAR(10) DEFAULT 'UAH',
    
    -- Classification
    cpv_code VARCHAR(20),  -- Common Procurement Vocabulary code
    cpv_description VARCHAR(500),
    
    -- Relationships
    buyer_id UUID REFERENCES buyers(id),
    winner_id UUID REFERENCES contractors(id),
    
    -- Award info
    award_value DECIMAL(20, 2),
    award_date DATE,
    
    -- Competition
    num_bids INTEGER DEFAULT 0,
    num_qualified_bids INTEGER DEFAULT 0,
    
    -- Dates
    tender_start_date TIMESTAMP WITH TIME ZONE,
    tender_end_date TIMESTAMP WITH TIME ZONE,
    date_modified TIMESTAMP WITH TIME ZONE,
    
    -- Location
    region VARCHAR(100),
    
    -- Risk scoring
    risk_score DECIMAL(5, 2),
    risk_category VARCHAR(20),
    risk_factors JSONB,  -- Detailed breakdown of risk signals
    risk_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Flags
    is_single_bidder BOOLEAN DEFAULT false,
    is_price_anomaly BOOLEAN DEFAULT false,
    is_bid_pattern_anomaly BOOLEAN DEFAULT false,
    
    -- Raw data
    raw_data JSONB,  -- Original Prozorro response
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tenders_prozorro_id ON tenders(prozorro_id);
CREATE INDEX idx_tenders_buyer ON tenders(buyer_id);
CREATE INDEX idx_tenders_winner ON tenders(winner_id);
CREATE INDEX idx_tenders_cpv ON tenders(cpv_code);
CREATE INDEX idx_tenders_region ON tenders(region);
CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_risk ON tenders(risk_score DESC);
CREATE INDEX idx_tenders_risk_category ON tenders(risk_category);
CREATE INDEX idx_tenders_date ON tenders(date_modified DESC);
CREATE INDEX idx_tenders_value ON tenders(expected_value DESC);
CREATE INDEX idx_tenders_single_bidder ON tenders(is_single_bidder) WHERE is_single_bidder = true;

-- ============================================================================

-- Bids (individual bids on tenders)
CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    contractor_id UUID NOT NULL REFERENCES contractors(id),
    
    -- Bid details
    bid_value DECIMAL(20, 2),
    currency VARCHAR(10) DEFAULT 'UAH',
    status VARCHAR(50),  -- 'active', 'unsuccessful', 'disqualified'
    
    -- Result
    is_winner BOOLEAN DEFAULT false,
    
    -- Dates
    bid_date TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_bids_tender ON bids(tender_id);
CREATE INDEX idx_bids_contractor ON bids(contractor_id);
CREATE INDEX idx_bids_tender_contractor ON bids(tender_id, contractor_id);
CREATE UNIQUE INDEX idx_bids_unique ON bids(tender_id, contractor_id);

-- ============================================================================

-- Co-bidding relationships (for network analysis)
CREATE TABLE co_bidding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contractor_a_id UUID NOT NULL REFERENCES contractors(id),
    contractor_b_id UUID NOT NULL REFERENCES contractors(id),
    
    -- Stats
    co_bid_count INTEGER DEFAULT 1,
    first_co_bid_date DATE,
    last_co_bid_date DATE,
    
    -- Analysis
    suspicion_score DECIMAL(5, 2),  -- How suspicious is this relationship
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure A < B to avoid duplicates
    CONSTRAINT co_bidding_order CHECK (contractor_a_id < contractor_b_id),
    CONSTRAINT co_bidding_unique UNIQUE (contractor_a_id, contractor_b_id)
);

CREATE INDEX idx_co_bidding_a ON co_bidding(contractor_a_id);
CREATE INDEX idx_co_bidding_b ON co_bidding(contractor_b_id);
CREATE INDEX idx_co_bidding_count ON co_bidding(co_bid_count DESC);

-- ============================================================================

-- Risk alerts (flagged high-risk items)
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- What's flagged
    alert_type VARCHAR(50) NOT NULL,  -- 'tender', 'contractor', 'network'
    tender_id UUID REFERENCES tenders(id),
    contractor_id UUID REFERENCES contractors(id),
    
    -- Alert details
    risk_score DECIMAL(5, 2) NOT NULL,
    risk_category VARCHAR(20) NOT NULL,
    reasons JSONB NOT NULL,  -- Array of reason strings
    
    -- Values at stake
    value_at_risk DECIMAL(20, 2),
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timing
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_tender ON alerts(tender_id);
CREATE INDEX idx_alerts_contractor ON alerts(contractor_id);
CREATE INDEX idx_alerts_risk ON alerts(risk_score DESC);
CREATE INDEX idx_alerts_active ON alerts(is_active) WHERE is_active = true;
CREATE INDEX idx_alerts_detected ON alerts(detected_at DESC);

-- ============================================================================

-- CPV category benchmarks (for price anomaly detection)
CREATE TABLE cpv_benchmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cpv_code VARCHAR(20) NOT NULL,
    cpv_description VARCHAR(500),
    
    -- Statistics
    sample_count INTEGER,
    mean_value DECIMAL(20, 2),
    median_value DECIMAL(20, 2),
    std_value DECIMAL(20, 2),
    p25_value DECIMAL(20, 2),
    p75_value DECIMAL(20, 2),
    
    -- Computed thresholds
    anomaly_threshold_high DECIMAL(20, 2),  -- Above this is suspicious
    anomaly_threshold_low DECIMAL(20, 2),   -- Below this is suspicious
    
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT cpv_benchmarks_unique UNIQUE (cpv_code)
);

CREATE INDEX idx_cpv_benchmarks_code ON cpv_benchmarks(cpv_code);

-- ============================================================================

-- Regional statistics
CREATE TABLE region_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    region VARCHAR(100) NOT NULL UNIQUE,
    
    -- Coordinates for map (center point)
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    
    -- Statistics
    total_tenders INTEGER DEFAULT 0,
    total_value DECIMAL(20, 2) DEFAULT 0,
    high_risk_tenders INTEGER DEFAULT 0,
    avg_risk_score DECIMAL(5, 2),
    single_bidder_rate DECIMAL(5, 4),
    
    -- Top issues
    top_risk_factors JSONB,
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_region_stats_region ON region_stats(region);
CREATE INDEX idx_region_stats_risk ON region_stats(avg_risk_score DESC);

-- ============================================================================

-- Sync tracking
CREATE TABLE sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type VARCHAR(50) NOT NULL,  -- 'full', 'incremental'
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    records_fetched INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'running',  -- 'running', 'completed', 'failed'
    error_message TEXT,
    
    metadata JSONB
);

CREATE INDEX idx_sync_log_type ON sync_log(sync_type);
CREATE INDEX idx_sync_log_started ON sync_log(started_at DESC);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contractors_updated
    BEFORE UPDATE ON contractors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_buyers_updated
    BEFORE UPDATE ON buyers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_tenders_updated
    BEFORE UPDATE ON tenders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Normalize name function
CREATE OR REPLACE FUNCTION normalize_name(input_name TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(input_name, '[""''«»]', '', 'g'),
            '\s+', ' ', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Auto-normalize contractor names
CREATE OR REPLACE FUNCTION normalize_contractor_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.name_normalized = normalize_name(NEW.name);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contractors_normalize
    BEFORE INSERT OR UPDATE OF name ON contractors
    FOR EACH ROW
    EXECUTE FUNCTION normalize_contractor_name();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- High-risk tenders view (for alert feed)
CREATE VIEW v_high_risk_tenders AS
SELECT 
    t.id,
    t.prozorro_id,
    t.title,
    t.expected_value,
    t.award_value,
    t.num_bids,
    t.risk_score,
    t.risk_category,
    t.risk_factors,
    t.is_single_bidder,
    t.is_price_anomaly,
    t.date_modified,
    t.region,
    b.name as buyer_name,
    c.name as winner_name,
    c.edrpou as winner_edrpou
FROM tenders t
LEFT JOIN buyers b ON t.buyer_id = b.id
LEFT JOIN contractors c ON t.winner_id = c.id
WHERE t.risk_score >= 50
ORDER BY t.date_modified DESC;

-- Contractor summary view
CREATE VIEW v_contractor_summary AS
SELECT 
    c.id,
    c.edrpou,
    c.name,
    c.region,
    c.total_tenders,
    c.total_wins,
    c.win_rate,
    c.total_value_won,
    c.risk_score,
    c.risk_category,
    COUNT(DISTINCT cb.contractor_b_id) + COUNT(DISTINCT cb2.contractor_a_id) as network_connections
FROM contractors c
LEFT JOIN co_bidding cb ON c.id = cb.contractor_a_id
LEFT JOIN co_bidding cb2 ON c.id = cb2.contractor_b_id
GROUP BY c.id;

-- ============================================================================
-- SAMPLE DATA SEEDING (for development)
-- ============================================================================

-- Ukrainian regions with coordinates
INSERT INTO region_stats (region, latitude, longitude) VALUES
('Київська область', 50.4501, 30.5234),
('Харківська область', 49.9935, 36.2304),
('Одеська область', 46.4825, 30.7233),
('Дніпропетровська область', 48.4647, 35.0462),
('Львівська область', 49.8397, 24.0297),
('Запорізька область', 47.8388, 35.1396),
('Миколаївська область', 46.9750, 31.9946),
('Херсонська область', 46.6354, 32.6169),
('Донецька область', 48.0159, 37.8028),
('Чернігівська область', 51.4982, 31.2893),
('Сумська область', 50.9077, 34.7981),
('Полтавська область', 49.5883, 34.5514),
('Вінницька область', 49.2331, 28.4682),
('Житомирська область', 50.2547, 28.6587),
('Волинська область', 50.7593, 25.3424),
('Рівненська область', 50.6199, 26.2516),
('Івано-Франківська область', 48.9226, 24.7111),
('Тернопільська область', 49.5535, 25.5948),
('Хмельницька область', 49.4230, 26.9871),
('Черкаська область', 49.4444, 32.0598),
('Кіровоградська область', 48.5079, 32.2623),
('Чернівецька область', 48.2920, 25.9358),
('Закарпатська область', 48.6208, 22.2879),
('Луганська область', 48.5740, 39.3078),
('м. Київ', 50.4501, 30.5234)
ON CONFLICT (region) DO NOTHING;
