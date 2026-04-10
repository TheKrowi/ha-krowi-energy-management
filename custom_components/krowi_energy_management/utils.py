"""Utility helpers for Krowi Energy Management."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

# Maps unit string → (currency_factor, magnitude_wh)
# currency_factor: relative to € (c€ = 0.01, € = 1.0)
# magnitude_wh: Wh equivalent (Wh=1, kWh=1_000, MWh=1_000_000)
_UNIT_FACTORS: dict[str, tuple[float, int]] = {
    "c€/Wh": (0.01, 1),
    "€/Wh": (1.0, 1),
    "EUR/Wh": (1.0, 1),
    "c€/kWh": (0.01, 1_000),
    "€/kWh": (1.0, 1_000),
    "EUR/kWh": (1.0, 1_000),
    "c€/MWh": (0.01, 1_000_000),
    "€/MWh": (1.0, 1_000_000),
    "EUR/MWh": (1.0, 1_000_000),
}


def convert_unit(value: float, from_unit: str, to_unit: str) -> float | None:
    """Convert *value* from *from_unit* to *to_unit*.

    Supports all combinations of {c€, €} × {Wh, kWh, MWh}.
    Returns None and logs a warning when either unit is unrecognised.
    """
    from_factors = _UNIT_FACTORS.get(from_unit)
    to_factors = _UNIT_FACTORS.get(to_unit)

    if from_factors is None:
        _LOGGER.warning(
            "krowi_energy_management: unrecognised source unit '%s'; cannot convert value",
            from_unit,
        )
        return None

    if to_factors is None:
        _LOGGER.warning(
            "krowi_energy_management: unrecognised target unit '%s'; cannot convert value",
            to_unit,
        )
        return None

    from_currency, from_magnitude = from_factors
    to_currency, to_magnitude = to_factors

    factor = (from_currency / to_currency) * (to_magnitude / from_magnitude)
    return value * factor


def apply_fx(value: float, fx_entity_id: str | None, hass) -> float | None:
    """Apply FX multiplier to *value* if *fx_entity_id* is configured.

    Returns the FX-adjusted value, or None if the FX entity is unavailable
    or non-numeric.  If *fx_entity_id* is empty/None, returns *value* unchanged.
    """
    if not fx_entity_id:
        return value

    state = hass.states.get(fx_entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        _LOGGER.warning(
            "krowi_energy_management: FX entity '%s' is unavailable; cannot compute price",
            fx_entity_id,
        )
        return None

    try:
        fx_rate = float(state.state)
    except (ValueError, TypeError):
        _LOGGER.warning(
            "krowi_energy_management: FX entity '%s' has non-numeric state '%s'",
            fx_entity_id,
            state.state,
        )
        return None

    return value * fx_rate


def safe_float_state(hass, entity_id: str) -> float | None:
    """Read the float state of *entity_id*, returning None when unavailable/unknown."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return None
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None
