"""Risk engine — pure, deterministic, no DB or LLM calls.

Five subscores (0-100, higher = more risk) and a composite formula.
All inputs are passed in; the engine is a pure function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
HUNDRED = Decimal("100")
ETF_CONCENTRATION_DISCOUNT = Decimal("0.4")


@dataclass
class HoldingInput:
    """Minimal holding data the engine needs."""

    ticker: str
    quantity: Decimal
    market_value: Decimal
    sector: str | None
    instrument_type: str  # "STOCK" or "ETF"
    beta: Decimal | None


@dataclass
class SubscoreResult:
    score: int
    explanation: str


@dataclass
class RiskEngineResult:
    overall_score: int
    concentration: SubscoreResult
    sector_concentration: SubscoreResult
    volatility: SubscoreResult
    diversification: SubscoreResult
    cash_ratio: SubscoreResult
    engine_explanation: str
    context: dict[str, str] = field(default_factory=dict)


def _clamp(value: Decimal, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))))


def _linear(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    """Linear interpolation between low (score=0) and high (score=100)."""
    if value <= low:
        return ZERO
    if value >= high:
        return HUNDRED
    return (value - low) / (high - low) * HUNDRED


# ── Subscore 1: Concentration ────────────────────────────────────────────


def compute_concentration_score(
    holdings: list[HoldingInput], total_value: Decimal
) -> SubscoreResult:
    """Max single-position weight. ETFs get 0.4 discount."""
    if not holdings or total_value <= 0:
        return SubscoreResult(score=0, explanation="No holdings.")

    max_weight = ZERO
    max_ticker = ""

    for h in holdings:
        weight = h.market_value / total_value
        effective = weight * ETF_CONCENTRATION_DISCOUNT if h.instrument_type == "ETF" else weight
        if effective > max_weight:
            max_weight = effective
            max_ticker = h.ticker

    raw_score = _linear(max_weight, Decimal("0.10"), Decimal("0.50"))
    score = _clamp(raw_score)

    actual_weight = ZERO
    for h in holdings:
        if h.ticker == max_ticker:
            actual_weight = h.market_value / total_value * HUNDRED
            break

    explanation = f"{actual_weight:.0f}% of portfolio is in {max_ticker}."
    return SubscoreResult(score=score, explanation=explanation)


# ── Subscore 2: Sector Concentration ─────────────────────────────────────


def compute_sector_concentration_score(
    holdings: list[HoldingInput], total_value: Decimal
) -> SubscoreResult:
    """Max sector weight. ETFs bucketed as 'Diversified'."""
    if not holdings or total_value <= 0:
        return SubscoreResult(score=0, explanation="No holdings.")

    sector_values: dict[str, Decimal] = {}
    for h in holdings:
        sector = "Diversified" if h.instrument_type == "ETF" else (h.sector or "Unknown")
        sector_values[sector] = sector_values.get(sector, ZERO) + h.market_value

    max_sector = ""
    max_weight = ZERO
    for sector, value in sector_values.items():
        # ETFs in "Diversified" don't count toward sector concentration
        if sector == "Diversified":
            continue
        weight = value / total_value
        if weight > max_weight:
            max_weight = weight
            max_sector = sector

    if not max_sector:
        return SubscoreResult(
            score=0, explanation="Holdings are diversified via ETFs."
        )

    raw_score = _linear(max_weight, Decimal("0.30"), Decimal("0.70"))
    score = _clamp(raw_score)

    pct = max_weight * HUNDRED
    explanation = f"{pct:.0f}% of portfolio is in {max_sector}."
    return SubscoreResult(score=score, explanation=explanation)


# ── Subscore 3: Volatility ───────────────────────────────────────────────


def compute_volatility_score(
    holdings: list[HoldingInput],
    total_value: Decimal,
) -> SubscoreResult:
    """Weighted portfolio beta. ETFs assumed beta=1.0, cash beta=0."""
    if not holdings or total_value <= 0:
        return SubscoreResult(score=0, explanation="No holdings.")

    weighted_beta = ZERO
    for h in holdings:
        weight = h.market_value / total_value
        beta = h.beta if h.beta is not None else Decimal("1.0")
        weighted_beta += weight * beta

    # Cash has beta=0 — since weights use total_value (incl. cash) as
    # denominator, the sum already reflects cash dilution.
    portfolio_beta = weighted_beta

    raw_score = _linear(portfolio_beta, Decimal("1.0"), Decimal("2.0"))
    score = _clamp(raw_score)

    explanation = f"Portfolio beta is {portfolio_beta:.2f}"
    if portfolio_beta > Decimal("1.0"):
        extra = ((portfolio_beta - Decimal("1.0")) * HUNDRED).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        explanation += f", {extra}% more volatile than the market."
    else:
        explanation += ", at or below market volatility."

    return SubscoreResult(score=score, explanation=explanation)


# ── Subscore 4: Diversification ──────────────────────────────────────────


def compute_diversification_score(
    holdings: list[HoldingInput],
    total_value: Decimal,
    cash: Decimal,
) -> SubscoreResult:
    """Blended: 0.6 * position_count_score + 0.4 * etf_ratio_score."""
    if not holdings:
        return SubscoreResult(
            score=0, explanation="No holdings. 100% cash."
        )

    position_count = len(holdings)

    # Position count score: 0 at >=15, 100 at <=1
    if position_count >= 15:
        pc_score = ZERO
    elif position_count <= 1:
        pc_score = HUNDRED
    else:
        pc_score = Decimal(15 - position_count) / Decimal(14) * HUNDRED

    # ETF ratio score: 0 at >=0.50, 60 at 0.00
    invested = total_value - cash
    if invested > 0:
        etf_value = sum(
            h.market_value for h in holdings if h.instrument_type == "ETF"
        )
        etf_ratio = etf_value / invested
    else:
        etf_ratio = ZERO

    if etf_ratio >= Decimal("0.50"):
        etf_score = ZERO
    elif etf_ratio <= ZERO:
        etf_score = Decimal("60")
    else:
        etf_score = (Decimal("1") - etf_ratio * 2) * Decimal("60")

    blended = Decimal("0.6") * pc_score + Decimal("0.4") * etf_score
    score = _clamp(blended)

    etf_pct = (etf_ratio * HUNDRED).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    explanation = (
        f"You hold {position_count} position{'s' if position_count != 1 else ''}."
        f" {etf_pct}% ETF exposure."
    )
    return SubscoreResult(score=score, explanation=explanation)


# ── Subscore 5: Cash Ratio ───────────────────────────────────────────────


def compute_cash_ratio_score(
    cash: Decimal, total_value: Decimal
) -> SubscoreResult:
    """U-shaped: too little or too much cash is risky."""
    if total_value <= 0:
        return SubscoreResult(score=0, explanation="No portfolio value.")

    ratio = cash / total_value

    if ratio <= Decimal("0.02"):
        raw = Decimal("70")
    elif ratio <= Decimal("0.05"):
        # Linear from 70 to 0 over [0.02, 0.05]
        raw = Decimal("70") * (Decimal("0.05") - ratio) / Decimal("0.03")
    elif ratio <= Decimal("0.30"):
        raw = ZERO
    elif ratio <= Decimal("0.80"):
        # Linear from 0 to 80 over [0.30, 0.80]
        raw = Decimal("80") * (ratio - Decimal("0.30")) / Decimal("0.50")
    else:
        raw = Decimal("80")

    score = _clamp(raw)
    pct = (ratio * HUNDRED).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    if ratio <= Decimal("0.02"):
        explanation = f"{pct}% cash — very low flexibility."
    elif ratio > Decimal("0.80"):
        explanation = f"{pct}% cash — most of your portfolio is uninvested."
    elif ratio > Decimal("0.30"):
        explanation = f"{pct}% cash — consider deploying more into the market."
    else:
        explanation = f"{pct}% cash is within healthy range."

    return SubscoreResult(score=score, explanation=explanation)


# ── Composite ────────────────────────────────────────────────────────────


def compute_overall_score(
    concentration: int,
    sector_concentration: int,
    volatility: int,
    diversification: int,
    cash_ratio: int,
) -> int:
    """Weighted average with max-floor for severe structural risks."""
    weighted_avg = (
        Decimal("0.30") * concentration
        + Decimal("0.25") * sector_concentration
        + Decimal("0.20") * volatility
        + Decimal("0.15") * diversification
        + Decimal("0.10") * cash_ratio
    )

    # Max-floor: only structural risks (not diversification/cash)
    max_structural = max(concentration, sector_concentration, volatility)
    floor = Decimal("0.85") * max_structural

    overall = max(weighted_avg, floor)
    return _clamp(overall)


# ── Main entry point ─────────────────────────────────────────────────────


def compute_risk_report(
    holdings: list[HoldingInput],
    cash: Decimal,
    total_value: Decimal,
) -> RiskEngineResult:
    """Compute the full risk report. Pure function, no side effects."""
    conc = compute_concentration_score(holdings, total_value)
    sect = compute_sector_concentration_score(holdings, total_value)
    vol = compute_volatility_score(holdings, total_value)
    div = compute_diversification_score(holdings, total_value, cash)
    cr = compute_cash_ratio_score(cash, total_value)

    overall = compute_overall_score(
        conc.score, sect.score, vol.score, div.score, cr.score
    )

    # Determine primary concern
    scores = {
        "concentration": conc.score,
        "sector_concentration": sect.score,
        "volatility": vol.score,
        "diversification": div.score,
        "cash_ratio": cr.score,
    }
    primary = max(scores, key=lambda k: scores[k])
    primary_labels = {
        "concentration": "single-position concentration",
        "sector_concentration": "sector concentration",
        "volatility": "portfolio volatility",
        "diversification": "lack of diversification",
        "cash_ratio": "cash allocation",
    }

    explanation = (
        f"Concentration risk: {conc.score}/100. {conc.explanation}\n"
        f"Sector concentration: {sect.score}/100. {sect.explanation}\n"
        f"Volatility: {vol.score}/100. {vol.explanation}\n"
        f"Diversification: {div.score}/100. {div.explanation}\n"
        f"Cash ratio: {cr.score}/100. {cr.explanation}\n"
        f"\nOverall risk score: {overall}/100.\n"
        f"Primary concern: {primary_labels[primary]}."
    )

    return RiskEngineResult(
        overall_score=overall,
        concentration=conc,
        sector_concentration=sect,
        volatility=vol,
        diversification=div,
        cash_ratio=cr,
        engine_explanation=explanation,
    )
