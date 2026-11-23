"""Abos & Verträge: Abos, Verträge und Beiträge verwalten und an Kündigungen erinnern."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .const import (
    CARD_URL,
    CONF_ZEIT,
    DEFAULT_ZEIT,
    DOMAIN,
    SERVICE_IMPORT,
    SERVICE_PRUEFEN,
    VERSION,
)
from .manager import AboManager

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type AboConfigEntry = ConfigEntry[AboManager]

IMPORT_SCHEMA = vol.Schema(
    {
        vol.Required("quelle"): cv.entity_id,
        vol.Required("ziel"): cv.entity_id,
        vol.Optional("erledigte", default=True): cv.boolean,
    }
)


def _managers(hass: HomeAssistant) -> list[AboManager]:
    return [
        e.runtime_data
        for e in hass.config_entries.async_entries(DOMAIN)
        if isinstance(getattr(e, "runtime_data", None), AboManager)
    ]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Karte bereitstellen und Aktionen anlegen (einmal pro Home Assistant)."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL,
                str(Path(__file__).parent / "frontend" / "abo-vertraege-card.js"),
                True,
            )
        ]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

    async def importieren(call: ServiceCall) -> dict:
        ziel = call.data["ziel"]
        manager = next((m for m in _managers(hass) if m.entity_id == ziel), None)
        if manager is None:
            raise HomeAssistantError(f"{ziel} ist keine Liste von Abos & Verträge")
        status = ["needs_action", "completed"] if call.data["erledigte"] else ["needs_action"]
        antwort = await hass.services.async_call(
            "todo",
            "get_items",
            {"entity_id": call.data["quelle"], "status": status},
            blocking=True,
            return_response=True,
        )
        eintraege = (antwort or {}).get(call.data["quelle"], {}).get("items", [])
        neu = await manager.async_import(eintraege)
        return {"uebernommen": neu, "gefunden": len(eintraege)}

    async def pruefen(call: ServiceCall) -> dict:
        verlaengert = gesendet = 0
        for manager in _managers(hass):
            verlaengert += await manager.async_verlaengern()
            gesendet += await manager.async_erinnern()
        return {"verlaengert": verlaengert, "erinnerungen": gesendet}

    hass.services.async_register(
        DOMAIN, SERVICE_IMPORT, importieren, IMPORT_SCHEMA, SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PRUEFEN, pruefen, vol.Schema({}), SupportsResponse.OPTIONAL
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AboConfigEntry) -> bool:
    manager = AboManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    stunde, minute, *_ = (str(entry.options.get(CONF_ZEIT, entry.data.get(CONF_ZEIT, DEFAULT_ZEIT))) + ":00").split(":")

    async def _nachts(_now) -> None:
        await manager.async_verlaengern()

    async def _erinnern(_now) -> None:
        await manager.async_erinnern()

    entry.async_on_unload(
        async_track_time_change(hass, _nachts, hour=0, minute=10, second=0)
    )
    entry.async_on_unload(
        async_track_time_change(
            hass, _erinnern, hour=int(stunde), minute=int(minute), second=0
        )
    )

    # Verpasste Verlängerungen (z. B. HA war nachts aus) beim Start nachholen.
    async def _gestartet(_hass) -> None:
        await manager.async_verlaengern()

    entry.async_on_unload(async_at_started(hass, _gestartet))

    entry.async_on_unload(entry.add_update_listener(_neu_laden))
    return True


async def _neu_laden(hass: HomeAssistant, entry: AboConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AboConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Gespeicherte Einträge löschen, wenn die Liste entfernt wird."""
    await AboManager(hass, entry).store.async_remove()
