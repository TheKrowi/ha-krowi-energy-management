"""Tests for custom_components.krowi_energy_management.utils."""
from unittest.mock import MagicMock

import pytest

from custom_components.krowi_energy_management.utils import (
    apply_fx,
    convert_unit,
    safe_float_state,
)


# ---------------------------------------------------------------------------
# convert_unit
# ---------------------------------------------------------------------------


def test_convert_unit_sameCurrency_sameUnit_returnsIdenticalValue():
    # Given / When
    actual = convert_unit(10.0, "c€/kWh", "c€/kWh")

    # Then
    assert actual == 10.0


def test_convert_unit_cEurKwh_to_eurKwh_dividesBy100():
    # Given / When
    actual = convert_unit(10.0, "c€/kWh", "€/kWh")

    # Then
    expected = 0.1
    assert actual == pytest.approx(expected)


def test_convert_unit_eurKwh_to_eurMWh_multipliesBy1000():
    # Given / When
    actual = convert_unit(0.1, "€/kWh", "€/MWh")

    # Then
    expected = 100.0
    assert actual == pytest.approx(expected)


def test_convert_unit_cEurKwh_to_eurMWh_appliesCombinedFactor():
    # Given / When
    actual = convert_unit(10.0, "c€/kWh", "€/MWh")

    # Then
    expected = 100.0
    assert actual == pytest.approx(expected)


def test_convert_unit_unknownFromUnit_returnsNone():
    # Given / When
    actual = convert_unit(1.0, "$/kWh", "€/kWh")

    # Then
    assert actual is None


def test_convert_unit_unknownToUnit_returnsNone():
    # Given / When
    actual = convert_unit(1.0, "€/kWh", "$/kWh")

    # Then
    assert actual is None


# ---------------------------------------------------------------------------
# apply_fx
# ---------------------------------------------------------------------------


def _make_hass_with_state(entity_id: str, state_value: str) -> MagicMock:
    hass = MagicMock()
    state = MagicMock()
    state.state = state_value
    hass.states.get.return_value = state
    return hass


def test_apply_fx_noFxEntityId_returnsValueUnchanged():
    # Given
    hass = MagicMock()

    # When
    actual = apply_fx(5.0, None, hass)

    # Then
    assert actual == 5.0


def test_apply_fx_emptyFxEntityId_returnsValueUnchanged():
    # Given
    hass = MagicMock()

    # When
    actual = apply_fx(5.0, "", hass)

    # Then
    assert actual == 5.0


def test_apply_fx_validFxEntity_returnsMultipliedValue():
    # Given
    hass = _make_hass_with_state("sensor.fx", "1.08")

    # When
    actual = apply_fx(10.0, "sensor.fx", hass)

    # Then
    expected = 10.8
    assert actual == pytest.approx(expected)


def test_apply_fx_fxEntityUnavailable_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.fx", "unavailable")

    # When
    actual = apply_fx(5.0, "sensor.fx", hass)

    # Then
    assert actual is None


def test_apply_fx_fxEntityUnknown_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.fx", "unknown")

    # When
    actual = apply_fx(5.0, "sensor.fx", hass)

    # Then
    assert actual is None


def test_apply_fx_fxEntityNonNumeric_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.fx", "not_a_number")

    # When
    actual = apply_fx(5.0, "sensor.fx", hass)

    # Then
    assert actual is None


def test_apply_fx_fxEntityMissing_returnsNone():
    # Given
    hass = MagicMock()
    hass.states.get.return_value = None

    # When
    actual = apply_fx(5.0, "sensor.fx", hass)

    # Then
    assert actual is None


# ---------------------------------------------------------------------------
# safe_float_state
# ---------------------------------------------------------------------------


def test_safe_float_state_validNumericState_returnsFloat():
    # Given
    hass = _make_hass_with_state("sensor.x", "3.14")

    # When
    actual = safe_float_state(hass, "sensor.x")

    # Then
    assert actual == pytest.approx(3.14)


def test_safe_float_state_unavailableState_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.x", "unavailable")

    # When
    actual = safe_float_state(hass, "sensor.x")

    # Then
    assert actual is None


def test_safe_float_state_unknownState_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.x", "unknown")

    # When
    actual = safe_float_state(hass, "sensor.x")

    # Then
    assert actual is None


def test_safe_float_state_entityNotFound_returnsNone():
    # Given
    hass = MagicMock()
    hass.states.get.return_value = None

    # When
    actual = safe_float_state(hass, "sensor.missing")

    # Then
    assert actual is None


def test_safe_float_state_nonNumericState_returnsNone():
    # Given
    hass = _make_hass_with_state("sensor.x", "abc")

    # When
    actual = safe_float_state(hass, "sensor.x")

    # Then
    assert actual is None
