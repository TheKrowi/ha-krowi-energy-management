"""Battery management control loop for Krowi Energy Management."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.event import async_track_time_interval  # type: ignore

from .const import (
    CONF_BATTERY_CONTROL_MODE_SWITCH,
    CONF_BATTERY_FORCE_MODE_SELECT,
    CONF_BATTERY_FORCIBLE_CHARGE_POWER_NUMBER,
    CONF_BATTERY_FORCIBLE_DISCHARGE_POWER_NUMBER,
    CONF_BATTERY_TARGET_CHARGE_POWER_SENSOR,
    CONF_BATTERY_TARGET_DISCHARGE_POWER_SENSOR,
    CONF_BATTERY_THRESHOLD,
    DEFAULT_BATTERY_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)

_LOOP_INTERVAL = timedelta(seconds=5)
_MODE_CHARGE = "charge"
_MODE_DISCHARGE = "discharge"


def _state_float(hass: HomeAssistant, entity_id: str | None, default: float = 0.0) -> float:
    """Return the float state of an entity, or *default* on missing/invalid state."""
    if not entity_id:
        return default
    state = hass.states.get(entity_id)
    if state is None:
        return default
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return default


class BatteryManager:
    """Implements the battery charge/discharge control loop.

    Mirrors the automation:
      - Every 5 s: ensure control-mode switch is on, then apply charge/discharge logic.
      - Charge block: if |target − current| >= threshold OR (target >= threshold AND mode ≠ 'charge')
        → set forcible charge power + set force mode to 'charge'.
      - Discharge block: same logic for discharge.

    The manager exposes `mode` (idle/charging/discharging) and `enabled` so that
    the companion switch and sensor entities can reflect its state.

    Future extension point: replace the two linked target-power sensors with
    internally computed values (e.g. from a PID controller or schedule).
    """

    def __init__(self, entry_id: str, config: dict) -> None:
        self._entry_id = entry_id
        self._config = config
        self._hass: HomeAssistant | None = None
        self._enabled: bool = True
        self._mode: str = "idle"
        self._unsub = None
        self._mode_listeners: list = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Current control mode: idle / charging / discharging."""
        return self._mode

    @property
    def enabled(self) -> bool:
        """Whether the management loop is active."""
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Enable or disable the management loop."""
        self._enabled = value

    def add_mode_listener(self, callback) -> None:
        """Register a callback invoked when mode changes."""
        self._mode_listeners.append(callback)

    def remove_mode_listener(self, callback) -> None:
        """Unregister a mode-change callback."""
        if callback in self._mode_listeners:
            self._mode_listeners.remove(callback)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant) -> None:
        """Start the 5-second control loop."""
        self._hass = hass
        self._unsub = async_track_time_interval(hass, self._async_run_loop, _LOOP_INTERVAL)
        _LOGGER.debug("Battery manager started for entry %s", self._entry_id)

    async def async_stop(self) -> None:
        """Stop the control loop."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        _LOGGER.debug("Battery manager stopped for entry %s", self._entry_id)

    # ------------------------------------------------------------------
    # Control loop
    # ------------------------------------------------------------------

    async def _async_run_loop(self, _now=None) -> None:
        if not self._enabled:
            return

        hass = self._hass
        cfg = self._config

        control_switch = cfg.get(CONF_BATTERY_CONTROL_MODE_SWITCH)
        target_charge_sensor = cfg.get(CONF_BATTERY_TARGET_CHARGE_POWER_SENSOR)
        target_discharge_sensor = cfg.get(CONF_BATTERY_TARGET_DISCHARGE_POWER_SENSOR)
        forcible_charge_number = cfg.get(CONF_BATTERY_FORCIBLE_CHARGE_POWER_NUMBER)
        forcible_discharge_number = cfg.get(CONF_BATTERY_FORCIBLE_DISCHARGE_POWER_NUMBER)
        force_mode_select = cfg.get(CONF_BATTERY_FORCE_MODE_SELECT)
        threshold = cfg.get(CONF_BATTERY_THRESHOLD, DEFAULT_BATTERY_THRESHOLD)

        # Step 1 — ensure control mode switch is on
        if control_switch:
            state = hass.states.get(control_switch)
            if state is None or state.state in ("off", "unavailable", "unknown"):
                await hass.services.async_call(
                    "switch",
                    "turn_on",
                    {"entity_id": control_switch},
                    blocking=False,
                )

        # Step 2 — read current values
        charge_target = _state_float(hass, target_charge_sensor)
        charge_current = _state_float(hass, forcible_charge_number)
        discharge_target = _state_float(hass, target_discharge_sensor)
        discharge_current = _state_float(hass, forcible_discharge_number)

        current_mode_state = hass.states.get(force_mode_select)
        current_mode = current_mode_state.state if current_mode_state else ""

        new_mode = "idle"

        # Step 3 — charge block
        if forcible_charge_number and force_mode_select:
            if abs(charge_target - charge_current) >= threshold or (
                charge_target >= threshold and current_mode != _MODE_CHARGE
            ):
                _LOGGER.debug(
                    "Battery %s: setting charge power=%.0f, mode=charge",
                    self._entry_id,
                    charge_target,
                )
                await hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": forcible_charge_number, "value": charge_target},
                    blocking=False,
                )
                await hass.services.async_call(
                    "select",
                    "select_option",
                    {"entity_id": force_mode_select, "option": _MODE_CHARGE},
                    blocking=False,
                )
                new_mode = "charging"

        # Step 4 — discharge block
        if forcible_discharge_number and force_mode_select:
            if abs(discharge_target - discharge_current) >= threshold or (
                discharge_target >= threshold and current_mode != _MODE_DISCHARGE
            ):
                _LOGGER.debug(
                    "Battery %s: setting discharge power=%.0f, mode=discharge",
                    self._entry_id,
                    discharge_target,
                )
                await hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": forcible_discharge_number, "value": discharge_target},
                    blocking=False,
                )
                await hass.services.async_call(
                    "select",
                    "select_option",
                    {"entity_id": force_mode_select, "option": _MODE_DISCHARGE},
                    blocking=False,
                )
                new_mode = "discharging"

        if new_mode != self._mode:
            self._mode = new_mode
            for listener in list(self._mode_listeners):
                listener()
