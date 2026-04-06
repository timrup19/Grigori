"""Add EDR directors tables and columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contractors",
        sa.Column("edr_status", sa.String(20), server_default="unknown", nullable=True),
    )
    op.add_column(
        "contractors",
        sa.Column("directors_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_contractors_edr_dissolved",
        "contractors",
        ["edr_status"],
        postgresql_where=sa.text("edr_status = 'dissolved'"),
    )

    op.create_table(
        "contractor_directors",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contractor_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contractors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=True),
        sa.Column("edrpou_person", sa.Text, nullable=True),
        sa.Column("source", sa.Text, server_default="edr"),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_contractor_directors_contractor",
        "contractor_directors",
        ["contractor_id"],
    )
    op.create_unique_constraint(
        "idx_contractor_directors_unique",
        "contractor_directors",
        ["contractor_id", "full_name"],
    )


def downgrade() -> None:
    op.drop_table("contractor_directors")
    op.drop_index("idx_contractors_edr_dissolved", table_name="contractors")
    op.drop_column("contractors", "directors_fetched_at")
    op.drop_column("contractors", "edr_status")
