"""Hält die Einträge einer Liste, speichert sie und erledigt die täglichen Aufgaben."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import date

from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import logic
from .const import (
    CONF_NOTIFY,
    CONF_FILTER,
    CONF_HA_PERSONEN,
    CONF_PERSONEN,
    CONF_MONATLICH,
    CONF_TAGE,
    CONF_TAGE_MONATLICH,
    DEFAULT_PERSONEN,
    DEFAULT_TAGE,
    DEFAULT_TAGE_MONATLICH,
    DOMAIN,
    FILTER_ZEILEN,
)

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


def _als_datum(wert) -> date | None:
    if wert is None or wert == "":
        return None
    if isinstance(wert, date):
        return wert if type(wert) is date else wert.date()
    try:
        return date.fromisoformat(str(wert)[:10])
    except ValueError:
        return None


def _status(wert) -> TodoItemStatus:
    """Status als TodoItemStatus, egal ob als Text oder Enum übergeben."""
    try:
        return TodoItemStatus(wert or TodoItemStatus.NEEDS_ACTION)
    except ValueError:
        return TodoItemStatus.NEEDS_ACTION


def _item_aus_dict(d: dict) -> TodoItem:
    return TodoItem(
        uid=d.get("uid") or uuid.uuid4().hex,
        summary=d.get("summary", ""),
        status=_status(d.get("status")),
        due=_als_datum(d.get("due")),
        description=d.get("description"),
    )


def _item_als_dict(i: TodoItem) -> dict:
    return {
        "uid": i.uid,
        "summary": i.summary,
        "status": _status(i.status).value,
        "due": i.due.isoformat() if i.due else None,
        "description": i.description,
    }


def ha_personen(hass: HomeAssistant) -> list[str]:
    """Vornamen aller in Home Assistant angelegten Personen, alphabetisch, ohne Doppelte."""
    namen = {logic.vorname(st.name) for st in hass.states.async_all("person")}
    return sorted((n for n in namen if n), key=str.casefold)


class AboManager:
    """Daten und Logik einer Abo-Liste."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.items: list[TodoItem] = []
        self.entity_id: str | None = None
        self._listeners: list[Callable[[], None]] = []

    # ---------- Einstellungen ----------
    def _opt(self, key, default):
        return self.entry.options.get(key, self.entry.data.get(key, default))

    @property
    def filterzeilen(self) -> list[str]:
        """Filterzeilen der Karte in fester Reihenfolge."""
        gewaehlt = self._opt(CONF_FILTER, FILTER_ZEILEN)
        return [z for z in FILTER_ZEILEN if z in gewaehlt]

    @property
    def personen(self) -> list[str]:
        """Personen aus Home Assistant (falls gewählt) plus zusätzliche Namen."""
        namen: list[str] = []
        if self._opt(CONF_HA_PERSONEN, True):
            namen = ha_personen(self.hass)
        return logic.personen_liste(namen + logic.personen_liste(self._opt(CONF_PERSONEN, DEFAULT_PERSONEN)))

    # ---------- Speicher ----------
    async def async_load(self) -> None:
        daten = await self.store.async_load() or {}
        self.items = [_item_aus_dict(d) for d in daten.get("items", [])]

    async def _async_save(self) -> None:
        await self.store.async_save({"items": [_item_als_dict(i) for i in self.items]})
        for listener in list(self._listeners):
            listener()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    # ---------- Bearbeiten ----------
    def _index(self, uid: str) -> int:
        for n, item in enumerate(self.items):
            if item.uid == uid:
                return n
        raise ValueError(f"Eintrag {uid} nicht gefunden")

    async def async_create(self, item: TodoItem) -> None:
        item.uid = uuid.uuid4().hex
        item.status = _status(item.status)
        self.items.append(item)
        await self._async_save()

    async def async_update(self, item: TodoItem) -> None:
        # Die Aktion todo.update_item liefert den Status als Text ("completed").
        item.status = _status(item.status)
        self.items[self._index(item.uid)] = item
        await self._async_save()

    async def async_delete(self, uids: list[str]) -> None:
        weg = set(uids)
        self.items = [i for i in self.items if i.uid not in weg]
        await self._async_save()

    async def async_move(self, uid: str, previous_uid: str | None) -> None:
        item = self.items.pop(self._index(uid))
        ziel = 0 if previous_uid is None else self._index(previous_uid) + 1
        self.items.insert(ziel, item)
        await self._async_save()

    async def async_import(self, eintraege: list[dict]) -> int:
        vorhanden = {(i.summary, i.due) for i in self.items}
        neu = 0
        for d in eintraege:
            item = _item_aus_dict({**d, "uid": None})
            if (item.summary, item.due) in vorhanden:
                continue
            self.items.append(item)
            neu += 1
        await self._async_save()
        return neu

    # ---------- Tägliche Aufgaben ----------
    async def async_verlaengern(self, heute: date | None = None) -> int:
        """Abgelaufene, nicht gekündigte Einträge mit Verlängerung weitersetzen."""
        heute = heute or dt_util.now().date()
        geaendert = 0
        for n, item in enumerate(self.items):
            if item.status != TodoItemStatus.NEEDS_ACTION or not item.due:
                continue
            e = logic.parse(item.description)
            neu = logic.neues_ende(item.due, e.monate, heute)
            if neu is None:
                continue
            self.items[n] = TodoItem(
                uid=item.uid,
                summary=item.summary,
                status=item.status,
                due=neu,
                description=logic.compose(e, neu),
            )
            geaendert += 1
        if geaendert:
            _LOGGER.debug("%s Einträge verlängert", geaendert)
            await self._async_save()
        return geaendert

    async def async_erinnern(self, heute: date | None = None) -> int:
        """Fällige Erinnerungen verschicken."""
        heute = heute or dt_util.now().date()
        tage = logic.tage_liste(self._opt(CONF_TAGE, DEFAULT_TAGE))
        tage_monatlich = (
            logic.tage_liste(self._opt(CONF_TAGE_MONATLICH, DEFAULT_TAGE_MONATLICH))
            if self._opt(CONF_MONATLICH, True)
            else []
        )
        ziele: list[str] = self._opt(CONF_NOTIFY, []) or []
        gesendet = 0
        for item in self.items:
            if item.status != TodoItemStatus.NEEDS_ACTION or not item.due:
                continue
            meldung = logic.erinnerung(
                item.summary,
                item.due,
                logic.parse(item.description),
                heute,
                tage,
                tage_monatlich,
            )
            if meldung is None:
                continue
            gesendet += 1
            await self._async_senden(ziele, *meldung)
        return gesendet

    async def _async_senden(self, ziele: list[str], titel: str, text: str) -> None:
        if not ziele:
            # Ohne Ziel landet die Meldung in den Benachrichtigungen von HA.
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {"title": titel, "message": text},
                blocking=False,
            )
            return
        for ziel in ziele:
            try:
                if ziel.startswith("notify.") and self.hass.states.get(ziel):
                    await self.hass.services.async_call(
                        "notify",
                        "send_message",
                        {"entity_id": ziel, "title": titel, "message": text},
                        blocking=True,
                    )
                else:
                    name = ziel.removeprefix("notify.")
                    await self.hass.services.async_call(
                        "notify", name, {"title": titel, "message": text}, blocking=True
                    )
            except Exception:  # noqa: BLE001 - ein kaputtes Ziel soll die anderen nicht stoppen
                _LOGGER.exception("Benachrichtigung an %s fehlgeschlagen", ziel)
