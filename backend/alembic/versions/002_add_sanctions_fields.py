"""Add sanctions enrichment fields to contractors

Revision ID: 002
Revises: 001
Create Date: 2026-04-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contractors",
        sa.Column("is_sanctioned", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "contractors",
        sa.Column("is_pep", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "contractors",
        sa.Column(
            "sanctions_hits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="'[]'::jsonb",
        ),
    )
    op.add_column(
        "contractors",
        sa.Column(
            "enriched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Index for fast querying of sanctioned/PEP contractors
    op.create_index(
        "idx_contractors_is_sanctioned",
        "contractors",
        ["is_sanctioned"],
        postgresql_where=sa.text("is_sanctioned = true"),
    )
    op.create_index(
        "idx_contractors_is_pep",
        "contractors",
        ["is_pep"],
        postgresql_where=sa.text("is_pep = true"),
    )


def downgrade() -> None:
    op.drop_index("idx_contractors_is_pep", table_name="contractors")
    op.drop_index("idx_contractors_is_sanctioned", table_name="contractors")
    op.drop_column("contractors", "enriched_at")
    op.drop_column("contractors", "sanctions_hits")
    op.drop_column("contractors", "is_pep")
    op.drop_column("contractors", "is_sanctioned")
