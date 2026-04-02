"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ─────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ── contractors ────────────────────────────────────────────────────────────
    op.create_table(
        "contractors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("edrpou", sa.String(20), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("name_normalized", sa.String(500), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_tenders", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_wins", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_value_won", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("win_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("risk_category", sa.String(20), nullable=True),
        sa.Column("risk_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edrpou"),
    )
    op.create_index("idx_contractors_edrpou", "contractors", ["edrpou"])
    op.create_index("idx_contractors_region", "contractors", ["region"])
    op.create_index("idx_contractors_risk_category", "contractors", ["risk_category"])
    # GIN trigram index and descending index need raw SQL
    op.execute(
        "CREATE INDEX idx_contractors_name_trgm ON contractors "
        "USING gin(name_normalized gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX idx_contractors_risk ON contractors (risk_score DESC)"
    )

    # ── buyers ─────────────────────────────────────────────────────────────────
    op.create_table(
        "buyers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("prozorro_id", sa.String(100), nullable=True),
        sa.Column("edrpou", sa.String(20), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("name_normalized", sa.String(500), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("buyer_type", sa.String(50), nullable=True),
        sa.Column("total_tenders", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_value", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("avg_competition", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prozorro_id"),
    )
    op.create_index("idx_buyers_prozorro_id", "buyers", ["prozorro_id"])
    op.create_index("idx_buyers_region", "buyers", ["region"])
    op.execute(
        "CREATE INDEX idx_buyers_name_trgm ON buyers "
        "USING gin(name_normalized gin_trgm_ops)"
    )

    # ── tenders ────────────────────────────────────────────────────────────────
    op.create_table(
        "tenders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("prozorro_id", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("procurement_method", sa.String(50), nullable=True),
        sa.Column("procurement_method_type", sa.String(100), nullable=True),
        sa.Column("expected_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(10), server_default=sa.text("'UAH'"), nullable=True),
        sa.Column("cpv_code", sa.String(20), nullable=True),
        sa.Column("cpv_description", sa.String(500), nullable=True),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("award_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("award_date", sa.Date(), nullable=True),
        sa.Column("num_bids", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("num_qualified_bids", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("tender_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tender_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("risk_category", sa.String(20), nullable=True),
        sa.Column("risk_factors", postgresql.JSONB(), nullable=True),
        sa.Column("risk_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_single_bidder", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_price_anomaly", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_bid_pattern_anomaly", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prozorro_id"),
    )
    op.create_index("idx_tenders_prozorro_id", "tenders", ["prozorro_id"])
    op.create_index("idx_tenders_buyer", "tenders", ["buyer_id"])
    op.create_index("idx_tenders_winner", "tenders", ["winner_id"])
    op.create_index("idx_tenders_cpv", "tenders", ["cpv_code"])
    op.create_index("idx_tenders_region", "tenders", ["region"])
    op.create_index("idx_tenders_status", "tenders", ["status"])
    op.create_index("idx_tenders_risk_category", "tenders", ["risk_category"])
    op.execute("CREATE INDEX idx_tenders_risk ON tenders (risk_score DESC)")
    op.execute("CREATE INDEX idx_tenders_date ON tenders (date_modified DESC)")
    op.execute("CREATE INDEX idx_tenders_value ON tenders (expected_value DESC)")
    op.execute(
        "CREATE INDEX idx_tenders_single_bidder ON tenders (is_single_bidder) "
        "WHERE is_single_bidder = true"
    )

    # ── bids ───────────────────────────────────────────────────────────────────
    op.create_table(
        "bids",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bid_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(10), server_default=sa.text("'UAH'"), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("is_winner", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("bid_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contractor_id"], ["contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_bids_tender", "bids", ["tender_id"])
    op.create_index("idx_bids_contractor", "bids", ["contractor_id"])
    op.create_index("idx_bids_tender_contractor", "bids", ["tender_id", "contractor_id"])
    op.execute(
        "CREATE UNIQUE INDEX idx_bids_unique ON bids (tender_id, contractor_id)"
    )

    # ── co_bidding ─────────────────────────────────────────────────────────────
    op.create_table(
        "co_bidding",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("contractor_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("co_bid_count", sa.Integer(), server_default=sa.text("1"), nullable=True),
        sa.Column("first_co_bid_date", sa.Date(), nullable=True),
        sa.Column("last_co_bid_date", sa.Date(), nullable=True),
        sa.Column("suspicion_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("contractor_a_id < contractor_b_id", name="co_bidding_order"),
        sa.ForeignKeyConstraint(["contractor_a_id"], ["contractors.id"]),
        sa.ForeignKeyConstraint(["contractor_b_id"], ["contractors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contractor_a_id", "contractor_b_id", name="co_bidding_unique"),
    )
    op.create_index("idx_co_bidding_a", "co_bidding", ["contractor_a_id"])
    op.create_index("idx_co_bidding_b", "co_bidding", ["contractor_b_id"])
    op.execute("CREATE INDEX idx_co_bidding_count ON co_bidding (co_bid_count DESC)")

    # ── alerts ─────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_category", sa.String(20), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column("value_at_risk", sa.Numeric(20, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["contractor_id"], ["contractors.id"]),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alerts_type", "alerts", ["alert_type"])
    op.create_index("idx_alerts_tender", "alerts", ["tender_id"])
    op.create_index("idx_alerts_contractor", "alerts", ["contractor_id"])
    op.execute("CREATE INDEX idx_alerts_risk ON alerts (risk_score DESC)")
    op.execute("CREATE INDEX idx_alerts_detected ON alerts (detected_at DESC)")
    op.execute(
        "CREATE INDEX idx_alerts_active ON alerts (is_active) WHERE is_active = true"
    )

    # ── cpv_benchmarks ─────────────────────────────────────────────────────────
    op.create_table(
        "cpv_benchmarks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("cpv_code", sa.String(20), nullable=False),
        sa.Column("cpv_description", sa.String(500), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("mean_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("median_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("std_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("p25_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("p75_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("anomaly_threshold_high", sa.Numeric(20, 2), nullable=True),
        sa.Column("anomaly_threshold_low", sa.Numeric(20, 2), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpv_code", name="cpv_benchmarks_unique"),
    )
    op.create_index("idx_cpv_benchmarks_code", "cpv_benchmarks", ["cpv_code"])

    # ── region_stats ───────────────────────────────────────────────────────────
    op.create_table(
        "region_stats",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("total_tenders", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("total_value", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("high_risk_tenders", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("avg_risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("single_bidder_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("top_risk_factors", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region"),
    )
    op.create_index("idx_region_stats_region", "region_stats", ["region"])
    op.execute("CREATE INDEX idx_region_stats_risk ON region_stats (avg_risk_score DESC)")

    # ── sync_log ───────────────────────────────────────────────────────────────
    op.create_table(
        "sync_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("sync_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_fetched", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("records_created", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("records_updated", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("errors", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'running'"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sync_log_type", "sync_log", ["sync_type"])
    op.execute("CREATE INDEX idx_sync_log_started ON sync_log (started_at DESC)")

    # ── Functions & Triggers ───────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    for table in ("contractors", "buyers", "tenders"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at()
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION normalize_name(input_name TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN LOWER(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(input_name, '[""''«»]', '', 'g'),
                    '\\s+', ' ', 'g'
                )
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION normalize_contractor_name()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.name_normalized = normalize_name(NEW.name);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE TRIGGER trg_contractors_normalize
            BEFORE INSERT OR UPDATE OF name ON contractors
            FOR EACH ROW
            EXECUTE FUNCTION normalize_contractor_name()
    """)

    # ── Seed Ukrainian regions ─────────────────────────────────────────────────
    op.execute("""
        INSERT INTO region_stats (region, latitude, longitude) VALUES
        ('Київська область',            50.4501, 30.5234),
        ('Харківська область',           49.9935, 36.2304),
        ('Одеська область',              46.4825, 30.7233),
        ('Дніпропетровська область',     48.4647, 35.0462),
        ('Львівська область',            49.8397, 24.0297),
        ('Запорізька область',           47.8388, 35.1396),
        ('Миколаївська область',         46.9750, 31.9946),
        ('Херсонська область',           46.6354, 32.6169),
        ('Донецька область',             48.0159, 37.8028),
        ('Чернігівська область',         51.4982, 31.2893),
        ('Сумська область',              50.9077, 34.7981),
        ('Полтавська область',           49.5883, 34.5514),
        ('Вінницька область',            49.2331, 28.4682),
        ('Житомирська область',          50.2547, 28.6587),
        ('Волинська область',            50.7593, 25.3424),
        ('Рівненська область',           50.6199, 26.2516),
        ('Івано-Франківська область',    48.9226, 24.7111),
        ('Тернопільська область',        49.5535, 25.5948),
        ('Хмельницька область',          49.4230, 26.9871),
        ('Черкаська область',            49.4444, 32.0598),
        ('Кіровоградська область',       48.5079, 32.2623),
        ('Чернівецька область',          48.2920, 25.9358),
        ('Закарпатська область',         48.6208, 22.2879),
        ('Луганська область',            48.5740, 39.3078),
        ('м. Київ',                      50.4501, 30.5234)
        ON CONFLICT (region) DO NOTHING
    """)


def downgrade() -> None:
    # Drop triggers first
    for table in ("contractors", "buyers", "tenders"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated ON {table}")
    op.execute("DROP TRIGGER IF EXISTS trg_contractors_normalize ON contractors")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS normalize_contractor_name()")
    op.execute("DROP FUNCTION IF EXISTS normalize_name(TEXT)")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at()")

    # Drop tables in reverse dependency order
    op.drop_table("sync_log")
    op.drop_table("region_stats")
    op.drop_table("cpv_benchmarks")
    op.drop_table("alerts")
    op.drop_table("co_bidding")
    op.drop_table("bids")
    op.drop_table("tenders")
    op.drop_table("buyers")
    op.drop_table("contractors")
