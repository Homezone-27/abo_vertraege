"""To-do-Liste der Abos & Verträge."""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .manager import AboManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AboListe(entry.runtime_data, entry)])


class AboListe(TodoListEntity):
    """Die Liste; jeder Eintrag ist ein Abo oder Vertrag."""

    _attr_icon = "mdi:file-sign"
    _attr_should_poll = False
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, manager: AboManager, entry: ConfigEntry) -> None:
        self._manager = manager
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title

    async def async_added_to_hass(self) -> None:
        self._manager.entity_id = self.entity_id
        self.async_on_remove(self._manager.async_add_listener(self.async_write_ha_state))

        @callback
        def _personen_geaendert(event: Event) -> None:
            # Person in HA angelegt, umbenannt oder gelöscht: Liste in der Karte aktualisieren.
            if str(event.data.get("entity_id", "")).startswith("person."):
                self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _personen_geaendert)
        )

        @callback
        def _name_geaendert(data) -> bool:
            # Nur reagieren, wenn eine Person neu ist, verschwindet oder anders heißt
            # (nicht bei jedem Ortswechsel).
            if not str(data.get("entity_id", "")).startswith("person."):
                return False
            alt, neu = data.get("old_state"), data.get("new_state")
            return (alt is None) != (neu is None) or (alt and neu and alt.name != neu.name)

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_STATE_CHANGED, _personen_geaendert, event_filter=_name_geaendert
            )
        )

    @property
    def todo_items(self) -> list[TodoItem]:
        return list(self._manager.items)

    @property
    def extra_state_attributes(self) -> dict:
        # Die Karte liest die Personen von hier.
        return {
            "personen": self._manager.personen,
            "filterzeilen": self._manager.filterzeilen,
            "abo_vertraege": True,
        }

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self._manager.async_create(item)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        await self._manager.async_update(item)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        await self._manager.async_delete(uids)

    async def async_move_todo_item(self, uid: str, previous_uid: str | None = None) -> None:
        await self._manager.async_move(uid, previous_uid)
