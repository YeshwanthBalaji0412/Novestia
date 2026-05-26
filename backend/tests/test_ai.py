"""Tests for AI explanation service — caching, versioning, graceful failure."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.ai import AIExplanation
from novestia.services import ai_service


def _mock_generate(text: str = "Test explanation."):
    return patch(
        "novestia.services.ai_service.generate",
        new_callable=AsyncMock,
        return_value=text,
    )


def _mock_generate_error():
    from novestia.integrations.gemini import AIGenerationError

    return patch(
        "novestia.services.ai_service.generate",
        new_callable=AsyncMock,
        side_effect=AIGenerationError("API down"),
    )


# ── Cache tests ──────────────────────────────────────────────────────────


async def test_explain_stock_caches_result(
    session: AsyncSession,
) -> None:
    """First call generates, second returns from cache."""
    snapshot_data = {
        "company_name": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "instrument_type": "STOCK",
        "last_price": "300.00",
        "market_cap": "3000000000000",
        "pe_ratio": "30",
        "eps": "10",
        "beta": "1.2",
        "dividend_yield": "0.005",
        "week_52_low": "150",
        "week_52_high": "310",
    }

    with _mock_generate("Apple is a tech company.") as mock:
        result1 = await ai_service.explain_stock("AAPL", snapshot_data, session)
        assert result1["explanation"] == "Apple is a tech company."
        assert result1["cached"] is False
        assert mock.call_count == 1

        # Second call should hit cache
        result2 = await ai_service.explain_stock("AAPL", snapshot_data, session)
        assert result2["explanation"] == "Apple is a tech company."
        assert result2["cached"] is True
        assert mock.call_count == 1  # No additional Gemini call


async def test_explain_metric_caches_per_ticker(
    session: AsyncSession,
) -> None:
    """Same metric for different tickers gets separate cache entries."""
    with _mock_generate("P/E explanation for AAPL."):
        r1 = await ai_service.explain_metric("pe_ratio", "AAPL", "30", session)
        assert r1["cached"] is False

    with _mock_generate("P/E explanation for NVDA."):
        r2 = await ai_service.explain_metric("pe_ratio", "NVDA", "60", session)
        assert r2["cached"] is False

    # Verify two cache entries
    result = await session.execute(select(AIExplanation))
    entries = result.scalars().all()
    assert len(entries) == 2


async def test_explain_metric_without_ticker_caches_globally(
    session: AsyncSession,
) -> None:
    """Metric without ticker context uses a global cache key."""
    with _mock_generate("Beta measures volatility."):
        r1 = await ai_service.explain_metric("beta", None, None, session)
        assert r1["cached"] is False

        r2 = await ai_service.explain_metric("beta", None, None, session)
        assert r2["cached"] is True


# ── Prompt versioning tests ──────────────────────────────────────────────


async def test_prompt_version_invalidates_cache(
    session: AsyncSession,
) -> None:
    """Changing prompt_version forces regeneration."""
    # Store a v1 entry directly
    entry = AIExplanation(
        content_type="metric_explanation",
        cache_key=ai_service._cache_key("metric_explanation", "beta"),
        content="Old beta explanation.",
        model="gemini-2.5-flash",
        prompt_version="v0",  # Old version
    )
    session.add(entry)
    await session.flush()

    # Current code uses v1 — should NOT find the v0 cache
    with _mock_generate("New beta explanation."):
        result = await ai_service.explain_metric("beta", None, None, session)
        assert result["cached"] is False
        assert result["explanation"] == "New beta explanation."


# ── Graceful failure tests ───────────────────────────────────────────────


async def test_gemini_failure_returns_graceful_error(
    session: AsyncSession,
) -> None:
    """When Gemini fails, return None explanation instead of 500."""
    with _mock_generate_error():
        result = await ai_service.explain_stock(
            "FAIL",
            {"company_name": "Test", "exchange": "N/A"},
            session,
        )
        assert result["explanation"] is None
        assert result.get("error") == "AI unavailable"


async def test_risk_explanation_graceful_failure(
    session: AsyncSession,
) -> None:
    """Risk explanation also fails gracefully."""
    with _mock_generate_error():
        result = await ai_service.explain_risk(
            "Some engine output", "fake-report-id", session
        )
        assert result["interpretation"] is None
        assert result.get("error") == "AI unavailable"


# ── Determinism test ─────────────────────────────────────────────────────


async def test_cache_key_deterministic() -> None:
    """Same inputs always produce same cache key."""
    k1 = ai_service._cache_key("stock_overview", "AAPL")
    k2 = ai_service._cache_key("stock_overview", "AAPL")
    assert k1 == k2

    # Different inputs produce different keys
    k3 = ai_service._cache_key("stock_overview", "NVDA")
    assert k1 != k3
