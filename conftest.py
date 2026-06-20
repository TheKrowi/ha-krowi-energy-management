"""
conftest.py — stub missing homeassistant subpackages for unit tests.

pytest-homeassistant-custom-component (0.13.316) ships an incomplete
homeassistant package that is missing the util/, helpers/, and generated/
subpackages. The stubs below are injected into sys.modules before any test
module is imported, so the custom component modules can be collected and run.
"""
from __future__ import annotations

import sys
from datetime import datetime as _datetime, timezone as _timezone
from types import ModuleType
from unittest.mock import MagicMock


# Simple stub class for any HA class used as a base in our component classes.
# Using MagicMock() as a base causes metaclass conflicts; a plain object
# subclass avoids that.
class _HABase:
    """Minimal base-class stub for HA entity classes."""


def _stub(name: str, **attrs) -> ModuleType:
    """Inject a stub module into sys.modules if not already present.

    Sets __path__ so Python treats the stub as a package, enabling
    sub-module lookup via sys.modules. Also wires the module as an
    attribute of its parent stub if the parent is already registered.
    """
    if name not in sys.modules:
        m = ModuleType(name)
        m.__path__ = []          # mark as package — required for sub-module imports
        m.__package__ = name
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        if "." in name:
            parent_name, _, child_attr = name.rpartition(".")
            parent = sys.modules.get(parent_name)
            if parent is not None:
                setattr(parent, child_attr, m)
    return sys.modules[name]


# ---------------------------------------------------------------------------
# homeassistant.core — stub to prevent loading the broken core.py
# (it fails at "from . import util" because util/ does not exist)
# ---------------------------------------------------------------------------
_stub(
    "homeassistant.core",
    HomeAssistant=MagicMock(),
    callback=lambda f: f,
    SupportsResponse=MagicMock(),
    ServiceCall=MagicMock(),
)

# ---------------------------------------------------------------------------
# homeassistant.generated (imported by homeassistant.const)
# ---------------------------------------------------------------------------
_stub("homeassistant.generated")
_stub("homeassistant.generated.entity_platforms", EntityPlatforms=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.const — stub to prevent loading const.py which imports generated
# ---------------------------------------------------------------------------
_stub(
    "homeassistant.const",
    Platform=MagicMock(),
    EVENT_HOMEASSISTANT_STOP=MagicMock(),
)

# ---------------------------------------------------------------------------
# homeassistant.util (entirely absent from the installed package)
# ---------------------------------------------------------------------------
_stub("homeassistant.util", repr_helper=lambda d: repr(d))
_stub(
    "homeassistant.util.dt",
    utcnow=MagicMock(),
    utc_from_timestamp=MagicMock(),
    parse_datetime=MagicMock(),
    as_local=lambda dt: dt,
    now=lambda: _datetime.now(_timezone.utc),
)
_stub(
    "homeassistant.util.async_",
    cancelling=MagicMock(),
    create_eager_task=MagicMock(),
    get_scheduled_timer_handles=MagicMock(),
    run_callback_threadsafe=MagicMock(),
    shutdown_run_callback_threadsafe=MagicMock(),
)
_stub("homeassistant.util.event_type", EventType=str)
_stub("homeassistant.util.executor", InterruptibleThreadPoolExecutor=MagicMock())
_stub("homeassistant.util.hass_dict", HassDict=dict)
_stub("homeassistant.util.json", JsonObjectType=dict)
_stub("homeassistant.util.read_only_dict", ReadOnlyDict=dict)
_stub("homeassistant.util.timeout", TimeoutManager=MagicMock())
_stub("homeassistant.util.ulid", ulid_at_time=MagicMock(), ulid_now=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.helpers (entirely absent from the installed package)
# ---------------------------------------------------------------------------
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.json", json_bytes=MagicMock(), json_fragment=MagicMock())
_stub("homeassistant.helpers.typing", VolSchemaType=object)
_stub("homeassistant.helpers.aiohttp_client", async_get_clientsession=MagicMock())
_stub(
    "homeassistant.helpers.event",
    async_track_time_change=MagicMock(),
    async_track_time_interval=MagicMock(),
    async_call_later=MagicMock(),
    async_track_state_change_event=MagicMock(),
    TrackTemplate=MagicMock(),
    async_track_template_result=MagicMock(),
)
_stub("homeassistant.helpers.storage", Store=MagicMock())
_stub("homeassistant.helpers.config_validation")
_stub("homeassistant.helpers.entity_registry", async_get=MagicMock())
_stub(
    "homeassistant.helpers.issue_registry",
    IssueSeverity=MagicMock(),
    async_create_issue=MagicMock(),
    async_delete_issue=MagicMock(),
)
_stub(
    "homeassistant.helpers.dispatcher",
    async_dispatcher_send=MagicMock(),
    async_dispatcher_connect=MagicMock(),
)
_stub("homeassistant.helpers.device_registry", DeviceInfo=MagicMock())
_stub("homeassistant.helpers.entity_platform", AddEntitiesCallback=MagicMock())
_stub("homeassistant.helpers.restore_state", RestoreEntity=_HABase)
_stub("homeassistant.helpers.template", Template=MagicMock())
_stub(
    "homeassistant.helpers.selector",
    SelectSelector=MagicMock(),
    SelectSelectorConfig=MagicMock(),
    SelectSelectorMode=MagicMock(),
    EntitySelector=MagicMock(),
    EntitySelectorConfig=MagicMock(),
    NumberSelector=MagicMock(),
    NumberSelectorConfig=MagicMock(),
    NumberSelectorMode=MagicMock(),
    TextSelector=MagicMock(),
    TextSelectorConfig=MagicMock(),
    TextSelectorType=MagicMock(),
)
_Entity = type("Entity", (_HABase,), {"async_write_ha_state": lambda self: None})
_stub(
    "homeassistant.helpers.entity",
    Entity=_Entity,
)

# ---------------------------------------------------------------------------
# homeassistant.config_entries & friends
# ---------------------------------------------------------------------------
_stub(
    "homeassistant.config_entries",
    ConfigEntry=MagicMock(),
    ConfigFlow=type("ConfigFlow", (), {"__init_subclass__": classmethod(lambda cls, **kwargs: None)}),
    OptionsFlow=type("OptionsFlow", (), {}),
)
_stub("homeassistant.data_entry_flow")
_stub("homeassistant.loader")

# ---------------------------------------------------------------------------
# homeassistant.components
# ---------------------------------------------------------------------------
_stub("homeassistant.components")
_stub(
    "homeassistant.components.persistent_notification",
    async_create=MagicMock(),
    async_dismiss=MagicMock(),
)
_stub(
    "homeassistant.components.sensor",
    SensorEntity=type("SensorEntity", (_Entity,), {}),
    SensorDeviceClass=MagicMock(),
    SensorStateClass=MagicMock(),
)
_stub(
    "homeassistant.components.number",
    NumberEntity=type("NumberEntity", (_Entity,), {}),
    NumberMode=MagicMock(),
    RestoreNumber=type("RestoreNumber", (_Entity,), {}),
)
_stub("homeassistant.components.repairs")
_stub(
    "homeassistant.components.switch",
    SwitchEntity=type("SwitchEntity", (_Entity,), {}),
)

# ---------------------------------------------------------------------------
# Wire all stubs as attributes on their parent packages.
#
# pytest's monkeypatch.setattr resolves dotted string paths via getattr chains
# (not via importlib), so each stub must be reachable as an attribute of its
# parent, not only via sys.modules.  The `homeassistant` package init is a
# single docstring, so importing it here is safe.
# ---------------------------------------------------------------------------
import homeassistant as _ha_pkg  # noqa: E402  (package __init__ is just a docstring)

for _full_name, _mod in list(sys.modules.items()):
    if not _full_name.startswith("homeassistant."):
        continue
    _parent_name, _, _child_attr = _full_name.rpartition(".")
    _parent = sys.modules.get(_parent_name)
    if _parent is not None:
        setattr(_parent, _child_attr, _mod)
