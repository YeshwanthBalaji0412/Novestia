"""Enable TimescaleDB and convert price_history to hypertable.

Revision ID: 002
Revises: 001
Create Date: 2026-05-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # Drop the standard index — TimescaleDB will create its own internal indexes.
    # The composite PK (ticker, recorded_at) remains.
    op.drop_index("ix_price_history_ticker_recorded_at", table_name="price_history")

    # Convert to hypertable. The 'if_not_exists' parameter makes this idempotent.
    op.execute(
        "SELECT create_hypertable('price_history', 'recorded_at', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )

    # Re-create the index on the hypertable
    op.create_index(
        "ix_price_history_ticker_recorded_at",
        "price_history",
        ["ticker", "recorded_at"],
    )


def downgrade() -> None:
    # Note: Converting a hypertable back to a regular table is not supported
    # by TimescaleDB. The downgrade drops the table entirely and recreates it
    # as a regular table. This loses data — acceptable only during development.
    op.drop_index("ix_price_history_ticker_recorded_at", table_name="price_history")

    # We can't un-hypertable, but we can drop and recreate the extension.
    # In practice, downgrading past this point means re-running 001 + 002.
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE")
