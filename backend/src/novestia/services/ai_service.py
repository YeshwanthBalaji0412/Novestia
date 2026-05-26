"""AI explanation service with DB-backed caching and prompt versioning.

Cache key = hash(content_type + relevant_input_data).
Cache is partitioned by prompt_version so bumping the version
forces regeneration without a manual flush.
"""

from __future__ import annotations

import hashlib
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.integrations.gemini import AIGenerationError, generate
from novestia.models.ai import AIExplanation
from novestia.prompts import load_prompt

logger = structlog.stdlib.get_logger()

# Metric display labels
METRIC_LABELS: dict[str, str] = {
    "pe_ratio": "Price-to-Earnings (P/E) Ratio",
    "eps": "Earnings Per Share (EPS)",
    "market_cap": "Market Capitalization",
    "beta": "Beta (Volatility Measure)",
    "dividend_yield": "Dividend Yield",
    "expense_ratio": "Expense Ratio",
    "week_52_high": "52-Week High",
    "week_52_low": "52-Week Low",
}


def _cache_key(*parts: str) -> str:
    """Create a deterministic cache key from input parts."""
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:32]


async def _check_cache(
    content_type: str,
    cache_key: str,
    prompt_version: str,
    db: AsyncSession,
) -> str | None:
    """Check if a cached explanation exists."""
    result = await db.execute(
        select(AIExplanation).where(
            AIExplanation.content_type == content_type,
            AIExplanation.cache_key == cache_key,
            AIExplanation.prompt_version == prompt_version,
        )
    )
    cached = result.scalars().first()
    if cached:
        logger.info("ai_cache_hit", content_type=content_type)
        return cached.content
    return None


async def _store_cache(
    content_type: str,
    cache_key: str,
    prompt_version: str,
    content: str,
    db: AsyncSession,
) -> None:
    """Store a generated explanation in the cache."""
    entry = AIExplanation(
        content_type=content_type,
        cache_key=cache_key,
        content=content,
        model="gemini-2.5-flash",
        prompt_version=prompt_version,
    )
    db.add(entry)
    await db.flush()


async def explain_stock(
    ticker: str,
    snapshot_data: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate a beginner-friendly stock explanation."""
    prompt_name = "stock_overview_v1"
    prompt_version = "v1"
    cache_key = _cache_key("stock_overview", ticker)

    # Check cache
    cached = await _check_cache("stock_overview", cache_key, prompt_version, db)
    if cached:
        return {"explanation": cached, "cached": True}

    # Build prompt
    template = load_prompt(prompt_name)
    prompt = template.format(
        company_name=snapshot_data.get("company_name", ticker),
        ticker=ticker,
        exchange=snapshot_data.get("exchange", "N/A"),
        sector=snapshot_data.get("sector", "N/A"),
        industry=snapshot_data.get("industry", "N/A"),
        instrument_type=snapshot_data.get("instrument_type", "STOCK"),
        price=snapshot_data.get("last_price", "N/A"),
        market_cap=snapshot_data.get("market_cap", "N/A"),
        pe_ratio=snapshot_data.get("pe_ratio", "N/A"),
        eps=snapshot_data.get("eps", "N/A"),
        beta=snapshot_data.get("beta", "N/A"),
        dividend_yield=snapshot_data.get("dividend_yield", "N/A"),
        week_52_low=snapshot_data.get("week_52_low", "N/A"),
        week_52_high=snapshot_data.get("week_52_high", "N/A"),
    )

    try:
        text = await generate(prompt)
        await _store_cache("stock_overview", cache_key, prompt_version, text, db)
        return {"explanation": text, "cached": False}
    except AIGenerationError:
        return {"explanation": None, "cached": False, "error": "AI unavailable"}


async def explain_risk(
    engine_explanation: str,
    risk_report_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate a beginner-friendly risk interpretation."""
    prompt_name = "risk_interpretation_v1"
    prompt_version = "v1"
    cache_key = _cache_key("risk_interpretation", risk_report_id)

    cached = await _check_cache(
        "risk_interpretation", cache_key, prompt_version, db
    )
    if cached:
        return {"interpretation": cached, "cached": True}

    template = load_prompt(prompt_name)
    prompt = template.format(engine_explanation=engine_explanation)

    try:
        text = await generate(prompt)
        await _store_cache(
            "risk_interpretation", cache_key, prompt_version, text, db
        )
        return {"interpretation": text, "cached": False}
    except AIGenerationError:
        return {"interpretation": None, "cached": False, "error": "AI unavailable"}


async def explain_metric(
    metric_name: str,
    ticker: str | None,
    metric_value: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate a beginner-friendly metric explanation."""
    prompt_name = "metric_explanation_v1"
    prompt_version = "v1"

    # Cache key includes ticker if provided (contextualized)
    key_parts = ["metric_explanation", metric_name]
    if ticker:
        key_parts.append(ticker)
    cache_key = _cache_key(*key_parts)

    cached = await _check_cache(
        "metric_explanation", cache_key, prompt_version, db
    )
    if cached:
        return {"explanation": cached, "cached": True}

    label = METRIC_LABELS.get(metric_name, metric_name)
    context_line = ""
    if ticker and metric_value:
        context_line = f"For {ticker}, the current value is: {metric_value}"

    template = load_prompt(prompt_name)
    prompt = template.format(
        metric_name=metric_name,
        metric_label=label,
        context_line=context_line,
    )

    try:
        text = await generate(prompt)
        await _store_cache(
            "metric_explanation", cache_key, prompt_version, text, db
        )
        return {"explanation": text, "cached": False}
    except AIGenerationError:
        return {"explanation": None, "cached": False, "error": "AI unavailable"}
