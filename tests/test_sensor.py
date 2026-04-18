"""Tests for key sensor _update() methods in krowi_energy_management.sensor."""
from unittest.mock import MagicMock, patch

import pytest

# Patch homeassistant.helpers.event before importing sensor, to avoid side effects
import homeassistant.helpers.event  # noqa: F401


@pytest.fixture(autouse=True)
def _patch_write_ha_state(monkeypatch):
    """Prevent async_write_ha_state from reaching HA internals in all sensor tests."""
    monkeypatch.setattr(
        "homeassistant.helpers.entity.Entity.async_write_ha_state",
        MagicMock(),
    )

from custom_components.krowi_energy_management.sensor import (
    ElectricityExportPriceEurSensor,
    ElectricityImportPriceEurSensor,
    ElectricityImportPriceSensor,
    ElectricityImportCostT1Sensor,
    ElectricityNetCostSensor,
    ElectricitySurchargeFormulaSensor,
    ElectricitySurchargeSensor,
    ElectricitySupplierImportPriceSensor,
    ElectricityTotalExportRevenueSensor,
    ElectricityTotalImportCostSensor,
    GasCalorificValueSensor,
    GasConsumptionKwhSensor,
    GasCurrentPriceEurSensor,
    GasCurrentPriceSensor,
    GasCurrentPriceM3Sensor,
    GasSurchargeFormulaSensor,
    GasSurchargeSensor,
    GasTotalCostSensor,
)
from custom_components.krowi_energy_management.const import (
    DOMAIN,
    UID_ELECTRICITY_ENERGY_CONTRIBUTION,
    UID_ELECTRICITY_DISTRIBUTION_TRANSPORT,
    UID_ELECTRICITY_EXCISE_DUTY,
    UID_ELECTRICITY_EXPORT_REVENUE_T1,
    UID_ELECTRICITY_EXPORT_REVENUE_T2,
    UID_ELECTRICITY_GREEN_ENERGY,
    UID_ELECTRICITY_IMPORT_COST_T1,
    UID_ELECTRICITY_IMPORT_COST_T2,
    UID_ELECTRICITY_NET_COST,
    UID_ELECTRICITY_PRICE_IMPORT,
    UID_ELECTRICITY_PRICE_IMPORT_EUR,
    UID_ELECTRICITY_PRICE_EXPORT,
    UID_ELECTRICITY_PRICE_EXPORT_EUR,
    UID_ELECTRICITY_SPOT_CURRENT_PRICE,
    UID_ELECTRICITY_SURCHARGE_RATE,
    UID_ELECTRICITY_TOTAL_EXPORT_REVENUE,
    UID_ELECTRICITY_TOTAL_IMPORT_COST,
    UID_ELECTRICITY_VAT,
    UID_GAS_CALORIFIC_VALUE,
    UID_GAS_CONSUMPTION_KWH,
    UID_GAS_DISTRIBUTION,
    UID_GAS_ENERGY_CONTRIBUTION,
    UID_GAS_EXCISE_DUTY,
    UID_GAS_PRICE,
    UID_GAS_PRICE_EUR,
    UID_GAS_PRICE_M3,
    UID_GAS_SPOT_AVERAGE_PRICE,
    UID_GAS_SURCHARGE_RATE,
    UID_GAS_TRANSPORT,
    UID_GAS_VAT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass(states: dict[str, str] | None = None) -> MagicMock:
    """Build a minimal hass mock with controllable entity states."""
    hass = MagicMock()
    states = states or {}

    def _get_state(entity_id):
        if entity_id not in states:
            return None
        s = MagicMock()
        s.state = states[entity_id]
        return s

    hass.states.get.side_effect = _get_state
    hass.data = {DOMAIN: {}}
    return hass


def _make_device_info() -> MagicMock:
    return MagicMock()


def _resolve_entity_id_factory(uid_to_eid: dict[str, str]):
    """Return a _resolve_entity_id that maps uid → entity_id for the given dict."""
    def _resolve(hass, platform, uid):
        return uid_to_eid.get(uid)
    return _resolve


# ---------------------------------------------------------------------------
# ElectricitySurchargeSensor._update
# ---------------------------------------------------------------------------


def test_electricitySurcharge_allFourRatesAvailable_returnsSumRounded():
    # Given
    uid_map = {
        UID_ELECTRICITY_GREEN_ENERGY: "number.green",
        UID_ELECTRICITY_DISTRIBUTION_TRANSPORT: "number.dist",
        UID_ELECTRICITY_EXCISE_DUTY: "number.excise",
        UID_ELECTRICITY_ENERGY_CONTRIBUTION: "number.energy",
    }
    hass = _make_hass({
        "number.green": "1.0",
        "number.dist": "2.0",
        "number.excise": "3.0",
        "number.energy": "4.0",
    })
    sensor = ElectricitySurchargeSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value == pytest.approx(10.0)


def test_electricitySurcharge_someRatesUnavailable_treatsAsZero():
    # Given
    uid_map = {
        UID_ELECTRICITY_GREEN_ENERGY: "number.green",
        UID_ELECTRICITY_DISTRIBUTION_TRANSPORT: "number.dist",
        UID_ELECTRICITY_EXCISE_DUTY: None,
        UID_ELECTRICITY_ENERGY_CONTRIBUTION: None,
    }
    hass = _make_hass({
        "number.green": "5.0",
        "number.dist": "5.0",
    })
    sensor = ElectricitySurchargeSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# ElectricitySurchargeFormulaSensor._update
# ---------------------------------------------------------------------------


def test_electricitySurchargeFormula_allRatesAvailable_buildsFormatString():
    # Given
    uid_map = {
        UID_ELECTRICITY_GREEN_ENERGY: "number.green",
        UID_ELECTRICITY_DISTRIBUTION_TRANSPORT: "number.dist",
        UID_ELECTRICITY_EXCISE_DUTY: "number.excise",
        UID_ELECTRICITY_ENERGY_CONTRIBUTION: "number.energy",
    }
    hass = _make_hass({
        "number.green": "1.0",
        "number.dist": "2.0",
        "number.excise": "3.0",
        "number.energy": "4.0",
    })
    sensor = ElectricitySurchargeFormulaSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    expected = "1.00000 + 2.00000 + 3.00000 + 4.00000 = 10.00000 c€/kWh"
    assert sensor._attr_native_value == expected


def test_electricitySurchargeFormula_ratesMissing_usesZeroesInFormula():
    # Given
    uid_map = {
        UID_ELECTRICITY_GREEN_ENERGY: None,
        UID_ELECTRICITY_DISTRIBUTION_TRANSPORT: None,
        UID_ELECTRICITY_EXCISE_DUTY: None,
        UID_ELECTRICITY_ENERGY_CONTRIBUTION: None,
    }
    hass = _make_hass({})
    sensor = ElectricitySurchargeFormulaSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    expected = "0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 c€/kWh"
    assert sensor._attr_native_value == expected


# ---------------------------------------------------------------------------
# ElectricityImportPriceSensor._update
# ---------------------------------------------------------------------------


def test_electricityImportPrice_allSourcesAvailable_computesCorrectPrice():
    # Given
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: "sensor.spot",
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({
        "sensor.spot": "5.0",
        "sensor.surcharge": "10.0",
        "number.vat": "21.0",
    })
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then: (5 + 10) * (1 + 21/100) = 15 * 1.21 = 18.15
    assert sensor._attr_native_value == pytest.approx(18.15)
    assert sensor._attr_available is True


def test_electricityImportPrice_spotUnavailable_setsUnavailable():
    # Given
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: "sensor.spot",
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({"sensor.spot": "unavailable"})
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_electricityImportPrice_spotEntityMissing_setsUnavailable():
    # Given
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: None,
        UID_ELECTRICITY_SURCHARGE_RATE: None,
        UID_ELECTRICITY_VAT: None,
    }
    hass = _make_hass({})
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_electricityImportPrice_spotNonNumeric_setsUnavailable():
    # Given
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: "sensor.spot",
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({"sensor.spot": "abc"})
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_electricityImportPrice_surchargeUnavailable_treatsAsZero():
    # Given
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: "sensor.spot",
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({
        "sensor.spot": "5.0",
        "sensor.surcharge": "unavailable",
        "number.vat": "0.0",
    })
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then: surcharge = 0, vat = 0 → (5 + 0) * 1 = 5.0
    assert sensor._attr_native_value == pytest.approx(5.0)
    assert sensor._attr_available is True


# ---------------------------------------------------------------------------
# GasCurrentPriceSensor._update
# ---------------------------------------------------------------------------


def test_gasCurrentPrice_allSourcesAvailable_computesCorrectPrice():
    # Given
    uid_map = {
        UID_GAS_SPOT_AVERAGE_PRICE: "sensor.gas_spot",
        UID_GAS_SURCHARGE_RATE: "sensor.gas_surcharge",
        UID_GAS_VAT: "number.gas_vat",
    }
    hass = _make_hass({
        "sensor.gas_spot": "4.5",
        "sensor.gas_surcharge": "2.0",
        "number.gas_vat": "6.0",
    })
    sensor = GasCurrentPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then: (4.5 + 2.0) * (1 + 6/100) = 6.5 * 1.06 = 6.89
    assert sensor._attr_native_value == pytest.approx(6.89)
    assert sensor._attr_available is True


def test_gasCurrentPrice_spotUnavailable_setsUnavailable():
    # Given
    uid_map = {
        UID_GAS_SPOT_AVERAGE_PRICE: "sensor.gas_spot",
        UID_GAS_SURCHARGE_RATE: "sensor.gas_surcharge",
        UID_GAS_VAT: "number.gas_vat",
    }
    hass = _make_hass({"sensor.gas_spot": "unavailable"})
    sensor = GasCurrentPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# GasTotalCostSensor._update
# ---------------------------------------------------------------------------


def _make_gas_total_sensor(hass, gas_meter_entity="sensor.meter") -> GasTotalCostSensor:
    sensor = GasTotalCostSensor(hass, "entry1", gas_meter_entity, _make_device_info())
    sensor._attr_native_value = 0.0
    return sensor


def _gcv_store(gcv_value: float = 10.5) -> MagicMock:
    store = MagicMock()
    store.gcv = gcv_value
    return store


def test_gasTotalCost_firstReading_anchorsLastM3NoIncrement():
    # Given
    hass = _make_hass({"sensor.meter": "100.0"})
    sensor = _make_gas_total_sensor(hass)
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._last_m3 == 100.0
    assert sensor._attr_native_value == 0.0  # no increment on first reading


def test_gasTotalCost_positiveConsumption_accumulatesCost():
    # Given
    hass = _make_hass({
        "sensor.meter": "101.0",
        "sensor.gas_price_eur": "0.08",
    })
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store(gcv_value=10.5)

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then: delta=1.0, gcv=10.5, price=0.08 → increment=0.84
    assert sensor._attr_native_value == pytest.approx(0.84)
    assert sensor._last_m3 == 101.0


def test_gasTotalCost_negativeDeltaMeterReplaced_reanchorsWithoutCost():
    # Given
    hass = _make_hass({"sensor.meter": "5.0", "sensor.gas_price_eur": "0.08"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 500.0
    sensor._attr_native_value = 50.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._last_m3 == 5.0
    assert sensor._attr_native_value == 50.0  # unchanged


def test_gasTotalCost_zeroDelta_noIncrement():
    # Given
    hass = _make_hass({"sensor.meter": "100.0", "sensor.gas_price_eur": "0.08"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._attr_native_value = 10.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value == 10.0  # unchanged


def test_gasTotalCost_gcvUnavailable_skipsTick():
    # Given
    hass = _make_hass({"sensor.meter": "101.0", "sensor.gas_price_eur": "0.08"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._attr_native_value = 5.0
    hass.data[DOMAIN]["gcv_store"] = None  # no store

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value == 5.0  # unchanged


def test_gasTotalCost_priceUnavailableUsesLastKnown():
    # Given
    hass = _make_hass({
        "sensor.meter": "101.0",
        "sensor.gas_price_eur": "unavailable",
    })
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._last_known_price = 0.07
    hass.data[DOMAIN]["gcv_store"] = _gcv_store(gcv_value=10.0)

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    hass.data[DOMAIN]["gcv_store"] = _gcv_store(gcv_value=10.0)

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then: delta=1.0, gcv=10.0, price=0.07 → 0.7
    assert sensor._attr_native_value == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# ElectricityImportPriceSensor — additional missing-data cases
# ---------------------------------------------------------------------------


def test_electricityImportPrice_spotUnknown_setsUnavailable():
    # Given: "unknown" is a distinct HA state from "unavailable"
    uid_map = {
        UID_ELECTRICITY_SPOT_CURRENT_PRICE: "sensor.spot",
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({"sensor.spot": "unknown"})
    sensor = ElectricityImportPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# GasCurrentPriceSensor — additional missing-data cases
# ---------------------------------------------------------------------------


def test_gasCurrentPrice_spotUnknown_setsUnavailable():
    uid_map = {
        UID_GAS_SPOT_AVERAGE_PRICE: "sensor.gas_spot",
        UID_GAS_SURCHARGE_RATE: "sensor.gas_surcharge",
        UID_GAS_VAT: "number.gas_vat",
    }
    hass = _make_hass({"sensor.gas_spot": "unknown"})
    sensor = GasCurrentPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_gasCurrentPrice_vatMissing_treatsAsZero():
    # Surcharge and VAT both unavailable → falls back to 0 for both
    uid_map = {
        UID_GAS_SPOT_AVERAGE_PRICE: "sensor.gas_spot",
        UID_GAS_SURCHARGE_RATE: None,
        UID_GAS_VAT: None,
    }
    hass = _make_hass({"sensor.gas_spot": "4.0"})
    sensor = GasCurrentPriceSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # (4 + 0) * (1 + 0/100) = 4.0
    assert sensor._attr_native_value == pytest.approx(4.0)
    assert sensor._attr_available is True


# ---------------------------------------------------------------------------
# GasTotalCostSensor — additional missing-data cases
# ---------------------------------------------------------------------------


def test_gasTotalCost_meterUnknown_skipsTick():
    hass = _make_hass({"sensor.meter": "unknown"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._attr_native_value = 5.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == 5.0  # unchanged


def test_gasTotalCost_meterNonNumeric_skipsTick():
    hass = _make_hass({"sensor.meter": "abc"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._attr_native_value = 5.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == 5.0  # unchanged


def test_gasTotalCost_storePresentButGcvNone_skipsTick():
    hass = _make_hass({"sensor.meter": "101.0", "sensor.gas_price_eur": "0.08"})
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._attr_native_value = 5.0
    gcv_store = _gcv_store()
    gcv_store.gcv = None  # store exists but GCV not yet loaded
    hass.data[DOMAIN]["gcv_store"] = gcv_store

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == 5.0  # unchanged


# ---------------------------------------------------------------------------
# ElectricityImportPriceEurSensor._update
# ---------------------------------------------------------------------------


def test_electricityImportPriceEur_sourceAvailable_dividesByHundred():
    uid_map = {UID_ELECTRICITY_PRICE_IMPORT: "sensor.import_price"}
    hass = _make_hass({"sensor.import_price": "18.15"})
    sensor = ElectricityImportPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(0.1815)


def test_electricityImportPriceEur_sourceUnavailable_returnsNone():
    uid_map = {UID_ELECTRICITY_PRICE_IMPORT: "sensor.import_price"}
    hass = _make_hass({"sensor.import_price": "unavailable"})
    sensor = ElectricityImportPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None


def test_electricityImportPriceEur_sourceMissing_returnsNone():
    uid_map = {UID_ELECTRICITY_PRICE_IMPORT: None}
    hass = _make_hass({})
    sensor = ElectricityImportPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None


# ---------------------------------------------------------------------------
# ElectricityExportPriceEurSensor._update
# ---------------------------------------------------------------------------


def test_electricityExportPriceEur_sourceAvailable_dividesByHundred():
    uid_map = {UID_ELECTRICITY_PRICE_EXPORT: "sensor.export_price"}
    hass = _make_hass({"sensor.export_price": "4.70"})
    sensor = ElectricityExportPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(0.047)


def test_electricityExportPriceEur_sourceUnavailable_returnsNone():
    uid_map = {UID_ELECTRICITY_PRICE_EXPORT: "sensor.export_price"}
    hass = _make_hass({"sensor.export_price": "unavailable"})
    sensor = ElectricityExportPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None


# ---------------------------------------------------------------------------
# GasSurchargeSensor._update
# ---------------------------------------------------------------------------


def test_gasSurcharge_allFourRatesAvailable_returnsSumRounded():
    uid_map = {
        UID_GAS_TRANSPORT: "number.transport",
        UID_GAS_DISTRIBUTION: "number.dist",
        UID_GAS_EXCISE_DUTY: "number.excise",
        UID_GAS_ENERGY_CONTRIBUTION: "number.energy",
    }
    hass = _make_hass({
        "number.transport": "1.0",
        "number.dist": "2.0",
        "number.excise": "3.0",
        "number.energy": "4.0",
    })
    sensor = GasSurchargeSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(10.0)


def test_gasSurcharge_someRatesMissing_treatsAsZero():
    uid_map = {
        UID_GAS_TRANSPORT: "number.transport",
        UID_GAS_DISTRIBUTION: None,
        UID_GAS_EXCISE_DUTY: None,
        UID_GAS_ENERGY_CONTRIBUTION: "number.energy",
    }
    hass = _make_hass({
        "number.transport": "3.0",
        "number.energy": "2.0",
    })
    sensor = GasSurchargeSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# GasSurchargeFormulaSensor._update
# ---------------------------------------------------------------------------


def test_gasSurchargeFormula_allRatesAvailable_buildsFormatString():
    uid_map = {
        UID_GAS_TRANSPORT: "number.transport",
        UID_GAS_DISTRIBUTION: "number.dist",
        UID_GAS_EXCISE_DUTY: "number.excise",
        UID_GAS_ENERGY_CONTRIBUTION: "number.energy",
    }
    hass = _make_hass({
        "number.transport": "1.0",
        "number.dist": "2.0",
        "number.excise": "3.0",
        "number.energy": "4.0",
    })
    sensor = GasSurchargeFormulaSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    expected = "1.00000 + 2.00000 + 3.00000 + 4.00000 = 10.00000 c€/kWh"
    assert sensor._attr_native_value == expected


def test_gasSurchargeFormula_allRatesMissing_usesZeroesInFormula():
    uid_map = {
        UID_GAS_TRANSPORT: None,
        UID_GAS_DISTRIBUTION: None,
        UID_GAS_EXCISE_DUTY: None,
        UID_GAS_ENERGY_CONTRIBUTION: None,
    }
    hass = _make_hass({})
    sensor = GasSurchargeFormulaSensor(hass, "entry1", "c€/kWh", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    expected = "0.00000 + 0.00000 + 0.00000 + 0.00000 = 0.00000 c€/kWh"
    assert sensor._attr_native_value == expected


# ---------------------------------------------------------------------------
# GasCurrentPriceEurSensor._update
# ---------------------------------------------------------------------------


def test_gasCurrentPriceEur_sourceAvailable_dividesByHundred():
    uid_map = {UID_GAS_PRICE: "sensor.gas_price"}
    hass = _make_hass({"sensor.gas_price": "6.89"})
    sensor = GasCurrentPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(0.0689)


def test_gasCurrentPriceEur_sourceUnavailable_returnsNone():
    uid_map = {UID_GAS_PRICE: "sensor.gas_price"}
    hass = _make_hass({"sensor.gas_price": "unavailable"})
    sensor = GasCurrentPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None


def test_gasCurrentPriceEur_sourceMissing_returnsNone():
    uid_map = {UID_GAS_PRICE: None}
    hass = _make_hass({})
    sensor = GasCurrentPriceEurSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None


# ---------------------------------------------------------------------------
# GasCalorificValueSensor._on_update
# ---------------------------------------------------------------------------


def test_gasCalorificValue_storeHasGcv_setValueAndAvailable():
    hass = _make_hass({})
    gcv_store = MagicMock()
    gcv_store.gcv = 11.2
    gcv_store.history = {}
    gcv_store.data_is_fresh = True
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasCalorificValueSensor(hass, "entry1", _make_device_info())

    sensor._on_update()

    assert sensor._attr_native_value == pytest.approx(11.2)
    assert sensor._attr_available is True


def test_gasCalorificValue_storeAbsent_setsUnavailable():
    hass = _make_hass({})
    hass.data[DOMAIN]["gcv_store"] = None
    sensor = GasCalorificValueSensor(hass, "entry1", _make_device_info())

    sensor._on_update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_gasCalorificValue_storeGcvNone_setsUnavailable():
    hass = _make_hass({})
    gcv_store = MagicMock()
    gcv_store.gcv = None
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasCalorificValueSensor(hass, "entry1", _make_device_info())

    sensor._on_update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# GasCurrentPriceM3Sensor._update
# ---------------------------------------------------------------------------


def test_gasCurrentPriceM3_allAvailable_computesCorrectValue():
    # price_eur = 0.068 EUR/kWh, gcv = 10.5 kWh/m³ → 0.714 €/m³
    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    hass = _make_hass({"sensor.gas_price_eur": "0.068"})
    gcv_store = MagicMock()
    gcv_store.gcv = 10.5
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasCurrentPriceM3Sensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(0.068 * 10.5, rel=1e-5)
    assert sensor._attr_available is True


def test_gasCurrentPriceM3_gcvMissing_setsUnavailable():
    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    hass = _make_hass({"sensor.gas_price_eur": "0.068"})
    hass.data[DOMAIN]["gcv_store"] = None
    sensor = GasCurrentPriceM3Sensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_gasCurrentPriceM3_priceUnavailable_setsUnavailable():
    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    hass = _make_hass({"sensor.gas_price_eur": "unavailable"})
    gcv_store = MagicMock()
    gcv_store.gcv = 10.5
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasCurrentPriceM3Sensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# GasConsumptionKwhSensor._update
# ---------------------------------------------------------------------------


def test_gasConsumptionKwh_allAvailable_computesCorrectValue():
    # 100 m³ × 10.5 kWh/m³ = 1050 kWh
    hass = _make_hass({"sensor.meter": "100.0"})
    gcv_store = MagicMock()
    gcv_store.gcv = 10.5
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasConsumptionKwhSensor(hass, "entry1", "sensor.meter", _make_device_info())

    sensor._update()

    assert sensor._attr_native_value == pytest.approx(1050.0)
    assert sensor._attr_available is True


def test_gasConsumptionKwh_meterUnavailable_setsUnavailable():
    hass = _make_hass({"sensor.meter": "unavailable"})
    gcv_store = MagicMock()
    gcv_store.gcv = 10.5
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasConsumptionKwhSensor(hass, "entry1", "sensor.meter", _make_device_info())

    sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_gasConsumptionKwh_gcvMissing_setsUnavailable():
    hass = _make_hass({"sensor.meter": "100.0"})
    hass.data[DOMAIN]["gcv_store"] = None
    sensor = GasConsumptionKwhSensor(hass, "entry1", "sensor.meter", _make_device_info())

    sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_gasConsumptionKwh_meterNonNumeric_setsUnavailable():
    hass = _make_hass({"sensor.meter": "not_a_number"})
    gcv_store = MagicMock()
    gcv_store.gcv = 10.5
    hass.data[DOMAIN]["gcv_store"] = gcv_store
    sensor = GasConsumptionKwhSensor(hass, "entry1", "sensor.meter", _make_device_info())

    sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# _ElectricityTariffCostSensor (via ElectricityImportCostT1Sensor)
# ---------------------------------------------------------------------------


def _make_tariff_sensor(hass, meter_entity="sensor.kwh", price_entity="sensor.price"):
    sensor = ElectricityImportCostT1Sensor(
        hass, "entry1", meter_entity, price_entity, _make_device_info()
    )
    sensor._attr_native_value = 0.0
    return sensor


def test_tariffCost_firstReading_anchorsLastKwhNoIncrement():
    hass = _make_hass({"sensor.kwh": "200.0"})
    sensor = _make_tariff_sensor(hass)

    sensor._update()

    assert sensor._last_kwh == 200.0
    assert sensor._attr_native_value == 0.0


def test_tariffCost_positiveConsumption_accumulatesCost():
    # 5 kWh × 0.25 EUR/kWh = 1.25 EUR
    hass = _make_hass({"sensor.kwh": "205.0", "sensor.price": "0.25"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 200.0

    sensor._update()

    assert sensor._attr_native_value == pytest.approx(1.25)
    assert sensor._last_kwh == 205.0


def test_tariffCost_negativeDelta_reanchorsWithoutCost():
    hass = _make_hass({"sensor.kwh": "5.0", "sensor.price": "0.25"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 500.0
    sensor._attr_native_value = 50.0

    sensor._update()

    assert sensor._last_kwh == 5.0
    assert sensor._attr_native_value == 50.0  # unchanged


def test_tariffCost_zeroDelta_noIncrement():
    hass = _make_hass({"sensor.kwh": "200.0", "sensor.price": "0.25"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 200.0
    sensor._attr_native_value = 10.0

    sensor._update()

    assert sensor._attr_native_value == 10.0  # unchanged


def test_tariffCost_priceUnavailableUsesLastKnown():
    # 3 kWh × 0.20 EUR/kWh = 0.60 EUR
    hass = _make_hass({"sensor.kwh": "103.0", "sensor.price": "unavailable"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 100.0
    sensor._last_known_price = 0.20

    sensor._update()

    assert sensor._attr_native_value == pytest.approx(0.60)


def test_tariffCost_priceAndLastKnownBothNone_skipsTick():
    hass = _make_hass({"sensor.kwh": "103.0", "sensor.price": "unavailable"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 100.0
    sensor._last_known_price = None
    sensor._attr_native_value = 5.0

    sensor._update()

    assert sensor._attr_native_value == 5.0  # unchanged


def test_tariffCost_meterUnavailable_skipsTick():
    hass = _make_hass({"sensor.kwh": "unavailable"})
    sensor = _make_tariff_sensor(hass)
    sensor._last_kwh = 100.0
    sensor._attr_native_value = 5.0

    sensor._update()

    assert sensor._attr_native_value == 5.0  # unchanged


# ---------------------------------------------------------------------------
# ElectricityTotalImportCostSensor._update
# ---------------------------------------------------------------------------


def test_totalImportCost_bothAvailable_returnsSum():
    uid_map = {
        UID_ELECTRICITY_IMPORT_COST_T1: "sensor.t1",
        UID_ELECTRICITY_IMPORT_COST_T2: "sensor.t2",
    }
    hass = _make_hass({"sensor.t1": "10.0", "sensor.t2": "5.0"})
    sensor = ElectricityTotalImportCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(15.0)
    assert sensor._attr_available is True


def test_totalImportCost_onlyT1Available_returnT1():
    uid_map = {
        UID_ELECTRICITY_IMPORT_COST_T1: "sensor.t1",
        UID_ELECTRICITY_IMPORT_COST_T2: "sensor.t2",
    }
    hass = _make_hass({"sensor.t1": "10.0", "sensor.t2": "unavailable"})
    sensor = ElectricityTotalImportCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # T2 = None → treated as 0
    assert sensor._attr_native_value == pytest.approx(10.0)
    assert sensor._attr_available is True


def test_totalImportCost_bothUnavailable_setsUnavailable():
    uid_map = {
        UID_ELECTRICITY_IMPORT_COST_T1: "sensor.t1",
        UID_ELECTRICITY_IMPORT_COST_T2: "sensor.t2",
    }
    hass = _make_hass({"sensor.t1": "unavailable", "sensor.t2": "unavailable"})
    sensor = ElectricityTotalImportCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# ElectricityTotalExportRevenueSensor._update
# ---------------------------------------------------------------------------


def test_totalExportRevenue_bothAvailable_returnsSum():
    uid_map = {
        UID_ELECTRICITY_EXPORT_REVENUE_T1: "sensor.t1",
        UID_ELECTRICITY_EXPORT_REVENUE_T2: "sensor.t2",
    }
    hass = _make_hass({"sensor.t1": "8.0", "sensor.t2": "3.0"})
    sensor = ElectricityTotalExportRevenueSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(11.0)
    assert sensor._attr_available is True


def test_totalExportRevenue_bothUnavailable_setsUnavailable():
    uid_map = {
        UID_ELECTRICITY_EXPORT_REVENUE_T1: "sensor.t1",
        UID_ELECTRICITY_EXPORT_REVENUE_T2: "sensor.t2",
    }
    hass = _make_hass({"sensor.t1": "unavailable", "sensor.t2": "unavailable"})
    sensor = ElectricityTotalExportRevenueSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# ElectricityNetCostSensor._update
# ---------------------------------------------------------------------------


def test_electricityNetCost_bothAvailable_returnsImportMinusExport():
    uid_map = {
        UID_ELECTRICITY_TOTAL_IMPORT_COST: "sensor.import",
        UID_ELECTRICITY_TOTAL_EXPORT_REVENUE: "sensor.export",
    }
    hass = _make_hass({"sensor.import": "15.0", "sensor.export": "4.0"})
    sensor = ElectricityNetCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(11.0)
    assert sensor._attr_available is True


def test_electricityNetCost_canGoNegative():
    # Export > Import → net negative (prosumer net credit)
    uid_map = {
        UID_ELECTRICITY_TOTAL_IMPORT_COST: "sensor.import",
        UID_ELECTRICITY_TOTAL_EXPORT_REVENUE: "sensor.export",
    }
    hass = _make_hass({"sensor.import": "5.0", "sensor.export": "20.0"})
    sensor = ElectricityNetCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value == pytest.approx(-15.0)
    assert sensor._attr_available is True


def test_electricityNetCost_importMissing_setsUnavailable():
    uid_map = {
        UID_ELECTRICITY_TOTAL_IMPORT_COST: "sensor.import",
        UID_ELECTRICITY_TOTAL_EXPORT_REVENUE: "sensor.export",
    }
    hass = _make_hass({"sensor.import": "unavailable", "sensor.export": "4.0"})
    sensor = ElectricityNetCostSensor(hass, "entry1", _make_device_info())

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


# ---------------------------------------------------------------------------
# ElectricitySupplierImportPriceSensor._update
# ---------------------------------------------------------------------------


def _make_supplier_sensor(hass, epex_multiplier=1.061, epex_offset=0.0):
    catalog_params = {
        "epex_multiplier": epex_multiplier,
        "epex_offset_cEur_kwh": epex_offset,
        "includes_surcharge": False,
        "vat_exempt": False,
    }
    return ElectricitySupplierImportPriceSensor(
        hass, "entry1", "mega", catalog_params, _make_device_info()
    )


def test_supplierImportPrice_allAvailable_computesCorrectPrice():
    # epex_rlp=5.0, multiplier=1.061, offset=0.0, surcharge=10.0, vat=21%
    # result = (5.0 * 1.061 + 0.0 + 10.0) * 1.21 = 15.305 * 1.21 = 18.51905
    uid_map = {
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({
        "sensor.surcharge": "10.0",
        "number.vat": "21.0",
    })
    nordpool_store = MagicMock()
    nordpool_store.monthly_average_rlp = 5.0
    hass.data[DOMAIN]["nordpool_store"] = nordpool_store
    sensor = _make_supplier_sensor(hass)

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    expected = (5.0 * 1.061 + 0.0 + 10.0) * 1.21
    assert sensor._attr_native_value == pytest.approx(expected, rel=1e-5)
    assert sensor._attr_available is True


def test_supplierImportPrice_storeAbsent_setsUnavailable():
    uid_map = {
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({})
    hass.data[DOMAIN]["nordpool_store"] = None
    sensor = _make_supplier_sensor(hass)

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False


def test_supplierImportPrice_monthlyAverageRlpNone_setsUnavailable():
    uid_map = {
        UID_ELECTRICITY_SURCHARGE_RATE: "sensor.surcharge",
        UID_ELECTRICITY_VAT: "number.vat",
    }
    hass = _make_hass({"sensor.surcharge": "10.0", "number.vat": "21.0"})
    nordpool_store = MagicMock()
    nordpool_store.monthly_average_rlp = None
    hass.data[DOMAIN]["nordpool_store"] = nordpool_store
    sensor = _make_supplier_sensor(hass)

    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    assert sensor._attr_native_value is None
    assert sensor._attr_available is False

    # Given
    hass = _make_hass({
        "sensor.meter": "101.0",
        "sensor.gas_price_eur": "unavailable",
    })
    sensor = _make_gas_total_sensor(hass)
    sensor._last_m3 = 100.0
    sensor._last_known_price = None
    sensor._attr_native_value = 3.0
    hass.data[DOMAIN]["gcv_store"] = _gcv_store()

    uid_map = {UID_GAS_PRICE_EUR: "sensor.gas_price_eur"}
    with patch(
        "custom_components.krowi_energy_management.sensor._resolve_entity_id",
        side_effect=_resolve_entity_id_factory(uid_map),
    ):
        sensor._update()

    # Then
    assert sensor._attr_native_value == 3.0  # unchanged
