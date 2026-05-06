"""Atrias GCV (Gross Calorific Value) store for Krowi Energy Management."""
from __future__ import annotations

import csv
import io
import logging
import socket
import ssl
from datetime import date, datetime

from dateutil.relativedelta import relativedelta  # type: ignore

from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.helpers.event import async_call_later, async_track_time_change  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore

from .const import ATRIAS_GCV_API_URL, ATRIAS_SUBSCRIPTION_KEY, DOMAIN, SIGNAL_GCV_UPDATE

_LOGGER = logging.getLogger(__name__)

_STORAGE_KEY = f"{DOMAIN}_gcv_history"
_STORAGE_VERSION = 1

_ATRIAS_HOSTNAME = "api.atrias.be"

# GoDaddy Secure Certificate Authority - G2 intermediate certificate.
# api.atrias.be's TLS handshake omits this intermediate, causing
# CERTIFICATE_VERIFY_FAILED with certifi's CA bundle alone.
# Source: http://certificates.godaddy.com/repository/gdig2.crt (AIA in leaf cert)
_GODADDY_G2_INTERMEDIATE_PEM = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIE0DCCA7igAwIBAgIBBzANBgkqhkiG9w0BAQsFADCBgzELMAkGA1UEBhMCVVMx\n"
    "EDAOBgNVBAgTB0FyaXpvbmExEzARBgNVBAcTClNjb3R0c2RhbGUxGjAYBgNVBAoT\n"
    "EUdvRGFkZHkuY29tLCBJbmMuMTEwLwYDVQQDEyhHbyBEYWRkeSBSb290IENlcnRp\n"
    "ZmljYXRlIEF1dGhvcml0eSAtIEcyMB4XDTExMDUwMzA3MDAwMFoXDTMxMDUwMzA3\n"
    "MDAwMFowgbQxCzAJBgNVBAYTAlVTMRAwDgYDVQQIEwdBcml6b25hMRMwEQYDVQQH\n"
    "EwpTY290dHNkYWxlMRowGAYDVQQKExFHb0RhZGR5LmNvbSwgSW5jLjEtMCsGA1UE\n"
    "CxMkaHR0cDovL2NlcnRzLmdvZGFkZHkuY29tL3JlcG9zaXRvcnkvMTMwMQYDVQQD\n"
    "EypHbyBEYWRkeSBTZWN1cmUgQ2VydGlmaWNhdGUgQXV0aG9yaXR5IC0gRzIwggEi\n"
    "MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC54MsQ1K92vdSTYuswZLiBCGzD\n"
    "BNliF44v/z5lz4/OYuY8UhzaFkVLVat4a2ODYpDOD2lsmcgaFItMzEUz6ojcnqOv\n"
    "K/6AYZ15V8TPLvQ/MDxdR/yaFrzDN5ZBUY4RS1T4KL7QjL7wMDge87Am+GZHY23e\n"
    "cSZHjzhHU9FGHbTj3ADqRay9vHHZqm8A29vNMDp5T19MR/gd71vCxJ1gO7GyQ5HY\n"
    "pDNO6rPWJ0+tJYqlxvTV0KaudAVkV4i1RFXULSo6Pvi4vekyCgKUZMQWOlDxSq7n\n"
    "eTOvDCAHf+jfBDnCaQJsY1L6d8EbyHSHyLmTGFBUNUtpTrw700kuH9zB0lL7AgMB\n"
    "AAGjggEaMIIBFjAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAdBgNV\n"
    "HQ4EFgQUQMK9J47MNIMwojPX+2yz8LQsgM4wHwYDVR0jBBgwFoAUOpqFBxBnKLbv\n"
    "9r0FQW4gwZTaD94wNAYIKwYBBQUHAQEEKDAmMCQGCCsGAQUFBzABhhhodHRwOi8v\n"
    "b2NzcC5nb2RhZGR5LmNvbS8wNQYDVR0fBC4wLDAqoCigJoYkaHR0cDovL2NybC5n\n"
    "b2RhZGR5LmNvbS9nZHJvb3QtZzIuY3JsMEYGA1UdIAQ/MD0wOwYEVR0gADAzMDEG\n"
    "CCsGAQUFBwIBFiVodHRwczovL2NlcnRzLmdvZGFkZHkuY29tL3JlcG9zaXRvcnkv\n"
    "MA0GCSqGSIb3DQEBCwUAA4IBAQAIfmyTEMg4uJapkEv/oV9PBO9sPpyIBslQj6Zz\n"
    "91cxG7685C/b+LrTW+C05+Z5Yg4MotdqY3MxtfWoSKQ7CC2iXZDXtHwlTxFWMMS2\n"
    "RJ17LJ3lXubvDGGqv+QqG+6EnriDfcFDzkSnE3ANkR/0yBOtg2DZ2HKocyQetawi\n"
    "DsoXiWJYRBuriSUBAA/NxBti21G00w9RKpv0vHP8ds42pM3Z2Czqrpv1KrKQ0U11\n"
    "GIo/ikGQI31bS/6kA1ibRrLDYGCD+H1QQc7CoZDDu+8CL9IVVO5EFdkKrqeKM+2x\n"
    "LXY2JtwE65/3YR8V3Idv7kaWKK2hJn0KCacuBKONvPi8BDAB\n"
    "-----END CERTIFICATE-----"
)


def _build_atrias_ssl_context() -> ssl.SSLContext:
    """Build an SSL context for api.atrias.be with the embedded GoDaddy G2 intermediate.

    api.atrias.be omits the intermediate from its TLS handshake, causing
    CERTIFICATE_VERIFY_FAILED.  Loading the intermediate as additional trusted
    data lets Python complete the chain: leaf → G2 intermediate → G2 root (certifi).
    """
    try:
        import certifi  # type: ignore  # noqa: PLC0415
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata=_GODADDY_G2_INTERMEDIATE_PEM)
    return ctx


def _probe_atrias_ssl_blocking() -> None:
    """Blocking TLS handshake probe against api.atrias.be:443.  Raises on failure."""
    ctx = _build_atrias_ssl_context()
    with socket.create_connection((_ATRIAS_HOSTNAME, 443), timeout=10) as raw:
        with ctx.wrap_socket(raw, server_hostname=_ATRIAS_HOSTNAME):
            pass  # handshake successful


class GcvStore:
    """Fetches and caches monthly GCV values from the Atrias API.

    Target file: always prior calendar month (GCVYYYYMM.txt).
    The current month's file never exists — Atrias publishes M's data in early M+1.

    Fetch schedule:
    - Startup: gap-fill the last 12 prior months from HA storage, fetch any missing.
    - Midnight on 1st of month (00:00:01): reset data_is_fresh, trigger refill.
    - Daily at 06:00:01: retry if data_is_fresh is False.

    History is persisted in HA storage as { "YYYY-MM": float } (12-entry rolling window).
    GCV values are in kWh/m³.
    """

    def __init__(self, zone: str) -> None:
        self._zone = zone
        self._hass: HomeAssistant | None = None
        self._gcv: float | None = None
        self._history: dict[str, float] = {}
        self._data_is_fresh: bool = False
        self._unsubs: list = []
        self._store: Store | None = None

    # -------------------------------------------------------------------------
    # Public properties
    # -------------------------------------------------------------------------

    @property
    def gcv(self) -> float | None:
        """Current GCV for the configured GOS zone (kWh/m³), or None if unavailable."""
        return self._gcv

    @property
    def history(self) -> dict[str, float]:
        """12-month rolling history { 'YYYY-MM': float }, sorted chronologically."""
        return dict(sorted(self._history.items()))

    @property
    def data_is_fresh(self) -> bool:
        """True when the most recent prior-month file has been successfully fetched."""
        return self._data_is_fresh

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def async_start(self, hass: HomeAssistant) -> None:
        """Start the store: load history, fill gaps, subscribe to time events."""
        self._hass = hass
        self._store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)

        # Load persisted history
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._history = {k: float(v) for k, v in stored.items()}

        # SSL probe — log result at INFO so it is visible without debug logging
        try:
            await hass.async_add_executor_job(_probe_atrias_ssl_blocking)
            _LOGGER.info("GcvStore: SSL verification for %s OK", _ATRIAS_HOSTNAME)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("GcvStore: SSL verification probe failed: %s", exc)

        # Fill any missing months (bootstrap on first install; gap-fill after restarts)
        await self._fill_missing_history()
        self._refresh_gcv()

        # If no data was fetched (network not ready at boot), retry after HA has started
        if self._gcv is None:
            _LOGGER.debug("GcvStore: no data after initial fill, scheduling startup retry")

            @callback
            def _startup_retry(_now=None) -> None:
                self._hass.async_create_task(self._do_refresh())

            self._unsubs.append(async_call_later(hass, 60, _startup_retry))

        # Dispatch initial state to sensors
        async_dispatcher_send(self._hass, SIGNAL_GCV_UPDATE)

        # Midnight: check for 1st of month → advance target
        self._unsubs.append(
            async_track_time_change(hass, self._on_midnight, hour=0, minute=0, second=1)
        )
        # 06:00 daily retry
        self._unsubs.append(
            async_track_time_change(hass, self._on_six_am, hour=6, minute=0, second=1)
        )

    async def async_stop(self) -> None:
        """Stop the store: unsubscribe all time-change listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # -------------------------------------------------------------------------
    # Target month helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _target_month(reference: date | None = None) -> tuple[int, int]:
        """Return (year, month) of the prior calendar month."""
        ref = reference or date.today()
        d = ref - relativedelta(months=1)
        return d.year, d.month

    @staticmethod
    def _last_12_targets() -> list[tuple[int, int]]:
        """Return the 12 most recent prior-month (year, month) tuples, oldest first."""
        today = date.today()
        targets = []
        for i in range(11, -1, -1):
            d = today - relativedelta(months=i + 1)
            targets.append((d.year, d.month))
        return targets

    @staticmethod
    def _ym_key(year: int, month: int) -> str:
        return f"{year}-{month:02d}"

    # -------------------------------------------------------------------------
    # Fetch
    # -------------------------------------------------------------------------

    async def async_fetch_month(self, year: int, month: int) -> float | None:
        """Fetch GCV for (year, month) for the configured zone. Returns value or None."""
        path = (
            f"SectorData%2F02%20Gross%20Calorific%20Values%2F{year}%2F"
            f"GCV{year}{month:02d}.txt"
        )
        url = f"{ATRIAS_GCV_API_URL}{path}?subscription-key={ATRIAS_SUBSCRIPTION_KEY}"

        session = async_get_clientsession(self._hass)
        _ssl_ctx = _build_atrias_ssl_context()
        try:
            async with session.get(url, ssl=_ssl_ctx) as resp:
                if resp.status == 404:
                    _LOGGER.debug("GcvStore: GCV%d%02d.txt not yet published (404)", year, month)
                    return None
                resp.raise_for_status()
                text = await resp.text(encoding="utf-8-sig")
        except Exception as exc:
            _LOGGER.warning("GcvStore: failed to fetch GCV %d-%02d: %s", year, month, exc)
            return None

        return self._parse_zone_gcv(text, year, month)

    def _parse_zone_gcv(self, text: str, year: int, month: int) -> float | None:
        """Parse CSV text and return GCV for the configured zone, or None."""
        # The file has a header line before the real CSV header ("GCVMonth,ARSName,...")
        lines = text.splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if "GCVMonth" in line:
                header_idx = i
                break
        if header_idx is None:
            _LOGGER.warning("GcvStore: no CSV header found in GCV %d-%02d", year, month)
            return None

        csv_text = "\n".join(lines[header_idx:])
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            for row in reader:
                ars_name = (row.get("ARSName") or "").strip()
                if ars_name == self._zone:
                    raw = (row.get("GCVValue") or "").strip().strip('"').replace(",", ".")
                    return float(raw)
        except Exception as exc:
            _LOGGER.warning("GcvStore: failed to parse GCV %d-%02d: %s", year, month, exc)
            return None

        _LOGGER.warning(
            "GcvStore: zone '%s' not found in GCV %d-%02d", self._zone, year, month
        )
        return None

    # -------------------------------------------------------------------------
    # Gap-fill / bootstrap
    # -------------------------------------------------------------------------

    async def _fill_missing_history(self) -> None:
        """Fetch any of the last 12 prior-month files not already in history."""
        targets = self._last_12_targets()
        missing = [(y, m) for y, m in targets if self._ym_key(y, m) not in self._history]

        for year, month in missing:
            value = await self.async_fetch_month(year, month)
            if value is not None:
                key = self._ym_key(year, month)
                self._history[key] = value
                _LOGGER.debug("GcvStore: stored %s = %.4f kWh/m³", key, value)
                await self._save_history()

        self._prune_history()
        if missing:
            await self._save_history()

        # Freshness: most recent target successfully in history
        most_recent_key = self._ym_key(*targets[-1])
        self._data_is_fresh = most_recent_key in self._history

    def _refresh_gcv(self) -> None:
        """Update self._gcv from the most recent history entry."""
        if not self._history:
            self._gcv = None
            _LOGGER.debug("GcvStore: history is empty, gcv is None")
            return
        latest_key = max(self._history.keys())
        self._gcv = self._history[latest_key]
        _LOGGER.info("GcvStore: zone '%s' GCV = %.6f kWh/m³ (from %s)", self._zone, self._gcv, latest_key)

    def _prune_history(self) -> None:
        """Keep only the 12 most recent entries."""
        if len(self._history) > 12:
            for key in sorted(self._history.keys())[:-12]:
                del self._history[key]

    async def _save_history(self) -> None:
        """Persist history dict to HA storage."""
        if self._store is not None:
            await self._store.async_save(self._history)

    # -------------------------------------------------------------------------
    # Refresh (fill + update GCV + dispatch)
    # -------------------------------------------------------------------------

    async def _do_refresh(self) -> None:
        """Gap-fill history, refresh current GCV, dispatch update signal."""
        await self._fill_missing_history()
        self._refresh_gcv()
        async_dispatcher_send(self._hass, SIGNAL_GCV_UPDATE)

    # -------------------------------------------------------------------------
    # Time-change callbacks
    # -------------------------------------------------------------------------

    @callback
    def _on_midnight(self, now: datetime) -> None:
        """At midnight: if it's the 1st of month, advance target and refresh."""
        if now.day == 1:
            self._data_is_fresh = False
            self._hass.async_create_task(self._do_refresh())

    @callback
    def _on_six_am(self, now: datetime) -> None:
        """At 06:00: retry if not yet fresh."""
        if not self._data_is_fresh:
            self._hass.async_create_task(self._do_refresh())

    # -------------------------------------------------------------------------
    # Diagnostic actions (called by HA services)
    # -------------------------------------------------------------------------

    async def async_action_test_connection(self) -> dict:
        """Run a TLS handshake probe against api.atrias.be and return a result dict.

        Returns ``{"ok": bool, "error": str | None}``.
        """
        try:
            await self._hass.async_add_executor_job(_probe_atrias_ssl_blocking)
            return {"ok": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    async def async_action_test_fetch(self, year: int, month: int) -> dict:
        """Perform a fresh API fetch for (year, month) and return a detailed result dict.

        Does **not** modify store state or history.

        Returns::

            {
                "ok": bool,
                "target_month": "YYYY-MM",
                "zone": str,
                "http_status": int | None,
                "gcv_value": float | None,
                "error": str | None,
            }
        """
        path = (
            f"SectorData%2F02%20Gross%20Calorific%20Values%2F{year}%2F"
            f"GCV{year}{month:02d}.txt"
        )
        url = f"{ATRIAS_GCV_API_URL}{path}?subscription-key={ATRIAS_SUBSCRIPTION_KEY}"
        target_month = f"{year}-{month:02d}"

        session = async_get_clientsession(self._hass)
        _ssl_ctx = _build_atrias_ssl_context()
        http_status: int | None = None
        gcv_value: float | None = None
        error: str | None = None

        try:
            async with session.get(url, ssl=_ssl_ctx) as resp:
                http_status = resp.status
                if resp.status == 404:
                    error = "404 Not Found — file not yet published by Atrias"
                elif resp.status != 200:
                    resp.raise_for_status()
                else:
                    text = await resp.text(encoding="utf-8-sig")
                    gcv_value = self._parse_zone_gcv(text, year, month)
                    if gcv_value is None:
                        error = f"Parsed OK but zone '{self._zone}' not found in CSV"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        return {
            "ok": gcv_value is not None,
            "target_month": target_month,
            "zone": self._zone,
            "http_status": http_status,
            "gcv_value": gcv_value,
            "error": error,
        }

    def action_store_state(self) -> dict:
        """Return a snapshot of the current in-memory store state.

        Returns::

            {
                "zone": str,
                "gcv": float | None,
                "data_is_fresh": bool,
                "target_month": "YYYY-MM",
                "history_count": int,
                "history": {"YYYY-MM": float, ...},
            }
        """
        ty, tm = self._target_month()
        return {
            "zone": self._zone,
            "gcv": self._gcv,
            "data_is_fresh": self._data_is_fresh,
            "target_month": self._ym_key(ty, tm),
            "history_count": len(self._history),
            "history": dict(sorted(self._history.items())),
        }
