"""Initial schema — all tables from the data model design.

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === Domain 1: Identity ===

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("onboarded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    # === Domain 2: Portfolio ===

    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("starting_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("average_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("first_purchased_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("portfolio_id", "ticker", name="uq_holdings_portfolio_ticker"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("transaction_type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("execution_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 4), nullable=True),
        sa.Column("executed_after_hours", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("journal_note", sa.Text(), nullable=True),
        sa.Column(
            "executed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "transaction_type IN ('BUY', 'SELL')",
            name="ck_transactions_type",
        ),
    )
    op.create_index(
        "ix_transactions_portfolio_executed_at",
        "transactions",
        ["portfolio_id", "executed_at"],
    )
    op.create_index(
        "ix_transactions_portfolio_ticker",
        "transactions",
        ["portfolio_id", "ticker"],
    )

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_journal_entries_portfolio_created_at",
        "journal_entries",
        ["portfolio_id", "created_at"],
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column("total_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_portfolio_snapshots_portfolio_recorded_at",
        "portfolio_snapshots",
        ["portfolio_id", "recorded_at"],
    )

    # === Watchlists ===

    op.create_table(
        "watchlists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "watchlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlists.id"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "watchlist_id", "ticker", name="uq_watchlist_items_watchlist_ticker"
        ),
    )

    # === Domain 3: Market Data ===

    op.create_table(
        "stocks",
        sa.Column("ticker", sa.String(), primary_key=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("instrument_type", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("metadata_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "instrument_type IN ('STOCK', 'ETF')",
            name="ck_stocks_instrument_type",
        ),
    )

    op.create_table(
        "stock_snapshots",
        sa.Column(
            "ticker",
            sa.String(),
            sa.ForeignKey("stocks.ticker"),
            primary_key=True,
        ),
        sa.Column("last_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_close", sa.Numeric(18, 4), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("eps", sa.Numeric(10, 4), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(8, 6), nullable=True),
        sa.Column("week_52_high", sa.Numeric(18, 4), nullable=True),
        sa.Column("week_52_low", sa.Numeric(18, 4), nullable=True),
        sa.Column("beta", sa.Numeric(8, 4), nullable=True),
        sa.Column("expense_ratio", sa.Numeric(8, 6), nullable=True),
        sa.Column("snapshot_taken_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "price_history",
        sa.Column(
            "ticker",
            sa.String(),
            sa.ForeignKey("stocks.ticker"),
            primary_key=True,
        ),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), primary_key=True),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_price_history_ticker_recorded_at",
        "price_history",
        ["ticker", "recorded_at"],
    )

    # === Domain 4: AI and Risk ===

    op.create_table(
        "ai_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "content_type",
            "cache_key",
            "prompt_version",
            name="uq_ai_explanations_type_key_version",
        ),
    )

    op.create_table(
        "risk_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("concentration_score", sa.Integer(), nullable=True),
        sa.Column("sector_concentration_score", sa.Integer(), nullable=True),
        sa.Column("volatility_score", sa.Integer(), nullable=True),
        sa.Column("diversification_score", sa.Integer(), nullable=True),
        sa.Column("cash_ratio_score", sa.Integer(), nullable=True),
        sa.Column("engine_explanation", sa.Text(), nullable=False),
        sa.Column("ai_interpretation", sa.Text(), nullable=True),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_risk_reports_portfolio_computed_at",
        "risk_reports",
        ["portfolio_id", "computed_at"],
    )

    # === Domain 5: System ===

    op.create_table(
        "api_call_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "called_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_api_call_log_provider_called_at",
        "api_call_log",
        ["provider", "called_at"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("api_call_log")
    op.drop_table("risk_reports")
    op.drop_table("ai_explanations")
    op.drop_table("price_history")
    op.drop_table("stock_snapshots")
    op.drop_table("stocks")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("portfolio_snapshots")
    op.drop_table("journal_entries")
    op.drop_table("transactions")
    op.drop_table("holdings")
    op.drop_table("portfolios")
    op.drop_table("users")
