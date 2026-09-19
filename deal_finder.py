"""Underwriting and funnel logic for turning raw property records into
ranked acquisition targets.

Each property is a plain dict of inputs (see `analyze_property` for the
fields it reads). This module does not fetch data from MLS, tax records,
permits, etc. — it assumes that data has already been gathered into the
dict form below, and focuses on the reasoning layer: estimating a deal's
economics and narrowing a large list down to the strongest few.
"""

CONFIDENCE_LEVELS = ("low", "medium", "high")

_MOTIVATION_RULES = (
    (lambda p: p.get("price_reductions", 0) >= 2,
     lambda p: f"{p['price_reductions']} price reductions"),
    (lambda p: p.get("days_on_market", 0) >= 60,
     lambda p: f"{p['days_on_market']} days on market"),
    (lambda p: p.get("last_sale_year") is not None
     and p["last_sale_year"] <= 2010,
     lambda p: f"owner purchased {p.get('_years_owned', '?')} years ago"),
    (lambda p: p.get("is_vacant"), lambda p: "vacant property"),
    (lambda p: p.get("has_code_violations"), lambda p: "open code violations"),
    (lambda p: p.get("was_expired_or_withdrawn"),
     lambda p: "previously expired/withdrawn listing"),
)


def estimate_rehab_cost(property_data):
    """Return a rehab-cost estimate, using an explicit figure if given,
    otherwise falling back to sqft * cost-per-sqft assumptions."""
    if property_data.get("rehab_estimate") is not None:
        return property_data["rehab_estimate"]

    sqft = property_data.get("sqft")
    cost_per_sqft = property_data.get("rehab_cost_per_sqft")
    if sqft is None or cost_per_sqft is None:
        raise ValueError(
            "estimate_rehab_cost() requires either 'rehab_estimate' or "
            "both 'sqft' and 'rehab_cost_per_sqft'"
        )
    return sqft * cost_per_sqft


def estimate_acquisition_cost(property_data):
    """Total cash needed to acquire and carry the property through rehab,
    including closing costs and carrying costs."""
    asking_price = property_data.get("asking_price")
    if asking_price is None:
        raise ValueError(
            "estimate_acquisition_cost() requires 'asking_price'"
        )

    closing_cost_pct = property_data.get("closing_cost_pct", 0.02)
    carrying_cost_per_month = property_data.get("carrying_cost_per_month", 0)
    carrying_cost_months = property_data.get("carrying_cost_months", 0)

    closing_costs = asking_price * closing_cost_pct
    carrying_costs = carrying_cost_per_month * carrying_cost_months
    return asking_price + closing_costs + carrying_costs


def estimate_confidence(property_data):
    """Rate how much we trust the stabilized-value estimate, based on how
    much comp/data support backs it up."""
    comp_count = property_data.get("comparable_sale_count", 0)
    comp_spread_pct = property_data.get("comparable_value_spread_pct")

    if comp_count >= 5 and comp_spread_pct is not None and comp_spread_pct <= 0.1:
        return "high"
    if comp_count >= 2:
        return "medium"
    return "low"


def _reasons(property_data):
    reasons = []
    if property_data.get("last_sale_year") is not None:
        current_year = property_data.get("_current_year", 2026)
        property_data = dict(property_data)
        property_data["_years_owned"] = current_year - property_data["last_sale_year"]

    for condition, describe in _MOTIVATION_RULES:
        if condition(property_data):
            reasons.append(describe(property_data))
    return reasons


def analyze_property(property_data):
    """Compute the underwriting summary for a single property.

    Expected keys on `property_data` (all optional unless noted):
      asking_price (required), stabilized_value (required, e.g. from
      neighborhood comps), sqft, rehab_estimate OR rehab_cost_per_sqft,
      closing_cost_pct, carrying_cost_per_month, carrying_cost_months,
      days_on_market, price_reductions, last_sale_year, is_vacant,
      has_code_violations, was_expired_or_withdrawn,
      comparable_sale_count, comparable_value_spread_pct.

    Returns a dict with the estimated rehab cost, total acquisition cost,
    gross spread, a confidence rating, and the reasons the property
    surfaced.
    """
    stabilized_value = property_data.get("stabilized_value")
    if stabilized_value is None:
        raise ValueError("analyze_property() requires 'stabilized_value'")

    rehab_cost = estimate_rehab_cost(property_data)
    acquisition_cost = estimate_acquisition_cost(property_data)
    total_cost = acquisition_cost + rehab_cost
    spread = stabilized_value - total_cost
    confidence = estimate_confidence(property_data)

    return {
        "asking_price": property_data["asking_price"],
        "stabilized_value": stabilized_value,
        "rehab_cost": rehab_cost,
        "acquisition_cost": acquisition_cost,
        "total_cost": total_cost,
        "spread": spread,
        "confidence": confidence,
        "reasons": _reasons(property_data),
    }


_CONFIDENCE_WEIGHT = {"low": 0.5, "medium": 0.8, "high": 1.0}


def score_property(property_data):
    """Rank key: gross spread discounted by confidence."""
    analysis = analyze_property(property_data)
    return analysis["spread"] * _CONFIDENCE_WEIGHT[analysis["confidence"]]


def run_funnel(properties, stage_sizes=(500, 100, 25, 8, 3)):
    """Narrow a list of property dicts down through successive stages,
    each keeping only the top-scoring `size` properties from the one
    before it.

    Returns a list of stages (lists of property dicts), one per entry in
    `stage_sizes`, each sorted best-first by `score_property`.
    """
    if not properties:
        raise ValueError("run_funnel() requires a non-empty sequence")

    ranked = sorted(properties, key=score_property, reverse=True)
    stages = []
    for size in stage_sizes:
        ranked = ranked[:size]
        stages.append(ranked)
    return stages
