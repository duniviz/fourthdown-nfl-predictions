"""Evidence gates for player-prop research cards.

The functions in this module intentionally return PASS unless the quote is a
fresh DraftKings two-sided market and there is a meaningful archived,
calibrated sample for that exact statistic.  A projection alone is not a bet.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

FRESH_FOR_SECONDS = 3 * 60 * 60
MIN_CALIBRATION_SAMPLE = 40
MIN_CONFIDENCE_SAMPLE = 75


def american_to_decimal(price):
    """Return decimal odds, or None for a malformed/non-actionable price."""
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price) or price == 0:
        return None
    return 1 + price / 100 if price > 0 else 1 + 100 / abs(price)


def implied_probability(price):
    decimal = american_to_decimal(price)
    return None if decimal is None else 1 / decimal


def no_vig_probabilities(over_price, under_price):
    over = implied_probability(over_price)
    under = implied_probability(under_price)
    if over is None or under is None or over + under <= 0:
        return None
    total = over + under
    return {"over": over / total, "under": under / total}


def market_ev(probability, price):
    decimal = american_to_decimal(price)
    if decimal is None or probability is None:
        return None
    return probability * decimal - 1


def quote_is_fresh(quote, now=None):
    if not quote or str(quote.get("bookmaker", "draftkings")).lower() != "draftkings":
        return False
    try:
        updated = datetime.fromisoformat(str(quote["last_update"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    now = now or datetime.now(timezone.utc)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    age = (now - updated).total_seconds()
    return 0 <= age < FRESH_FOR_SECONDS


def recommendation(model_over_probability, quote, calibration, injury_uncertain=False, now=None):
    """Return a transparent recommendation payload for a two-sided O/U quote.

    Probability must be calibrated upstream.  This gate refuses to turn an
    exploratory simulation into a recommendation.
    """
    base = {
        "recommendation": "PASS", "confidence": "Low", "reason": None,
        "model_over_probability": None, "model_under_probability": None,
        "market_over_probability": None, "market_under_probability": None,
        "ev": None,
    }
    if not quote_is_fresh(quote, now):
        base["reason"] = "Fresh verified DraftKings quote unavailable"
        return base
    try:
        probability = float(model_over_probability)
    except (TypeError, ValueError):
        base["reason"] = "Calibrated model probability unavailable"
        return base
    if not 0 < probability < 1:
        base["reason"] = "Calibrated model probability unavailable"
        return base
    market = no_vig_probabilities(quote.get("over_price"), quote.get("under_price"))
    if market is None:
        base["reason"] = "Verified two-sided DraftKings prices unavailable"
        return base
    sample_size = int((calibration or {}).get("sample_size") or 0)
    calibrated = bool((calibration or {}).get("probability_calibrated"))
    if sample_size < MIN_CALIBRATION_SAMPLE or not calibrated:
        base["reason"] = "Insufficient archived probability calibration for this market"
        return base
    side = "OVER" if probability >= .5 else "UNDER"
    side_probability = probability if side == "OVER" else 1 - probability
    price = quote.get("over_price") if side == "OVER" else quote.get("under_price")
    ev = market_ev(side_probability, price)
    base.update({
        "model_over_probability": round(probability * 100, 1),
        "model_under_probability": round((1 - probability) * 100, 1),
        "market_over_probability": round(market["over"] * 100, 1),
        "market_under_probability": round(market["under"] * 100, 1),
        "ev": round((ev or 0) * 100, 1),
    })
    if injury_uncertain:
        base["reason"] = "Availability uncertainty requires a PASS"
        return base
    # A small edge buffer avoids recommending on ordinary simulation noise.
    if ev is None or ev < .025:
        base["reason"] = "No material estimated value after market price"
        return base
    base["recommendation"] = side
    base["confidence"] = "High" if sample_size >= MIN_CONFIDENCE_SAMPLE and ev >= .08 else "Medium"
    base["reason"] = "Calibrated probability and fresh DraftKings price clear the value gate"
    return base
