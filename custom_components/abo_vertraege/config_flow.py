"""Einrichtung und Optionen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from . import logic
from .manager import ha_personen
from .const import (
    CONF_FILTER,
    CONF_HA_PERSONEN,
    CONF_NAME,
    CONF_NOTIFY,
    CONF_PERSONEN,
    CONF_MONATLICH,
    CONF_TAGE,
    CONF_TAGE_MONATLICH,
    CONF_ZEIT,
    DEFAULT_NAME,
    DEFAULT_PERSONEN,
    DEFAULT_TAGE,
    DEFAULT_TAGE_MONATLICH,
    DEFAULT_ZEIT,
    DOMAIN,
    FILTER_ZEILEN,
)


def _notify_ziele(hass: HomeAssistant) -> list[str]:
    """Benachrichtigungs-Entitäten und klassische notify-Aktionen zur Auswahl."""
    entitaeten = sorted(hass.states.async_entity_ids("notify"))
    aktionen = sorted(
        f"notify.{name}"
        for name in hass.services.async_services_for_domain("notify")
        if name not in ("send_message", "persistent_notification")
    )
    return entitaeten + [a for a in aktionen if a not in entitaeten]


def _schema(hass: HomeAssistant, werte: dict[str, Any], mit_name: bool) -> vol.Schema:
    felder: dict = {}
    if mit_name:
        felder[vol.Required(CONF_NAME, default=werte.get(CONF_NAME, DEFAULT_NAME))] = TextSelector()
    felder[vol.Required(CONF_HA_PERSONEN, default=werte.get(CONF_HA_PERSONEN, True))] = BooleanSelector()
    weitere = logic.personen_liste(werte.get(CONF_PERSONEN, DEFAULT_PERSONEN))
    felder[vol.Optional(CONF_PERSONEN, default=weitere)] = SelectSelector(
        SelectSelectorConfig(
            options=logic.personen_liste(["Gemeinsam", *weitere]),
            multiple=True,
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )
    felder[vol.Optional(CONF_FILTER, default=werte.get(CONF_FILTER, FILTER_ZEILEN))] = SelectSelector(
        SelectSelectorConfig(
            options=FILTER_ZEILEN,
            multiple=True,
            mode=SelectSelectorMode.LIST,
            translation_key=CONF_FILTER,
        )
    )
    felder[vol.Optional(CONF_NOTIFY, default=werte.get(CONF_NOTIFY, []))] = SelectSelector(
        SelectSelectorConfig(
            options=_notify_ziele(hass),
            multiple=True,
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )
    felder[vol.Required(CONF_ZEIT, default=werte.get(CONF_ZEIT, DEFAULT_ZEIT))] = TimeSelector()
    felder[vol.Required(CONF_TAGE, default=werte.get(CONF_TAGE, DEFAULT_TAGE))] = TextSelector()
    felder[vol.Required(CONF_MONATLICH, default=werte.get(CONF_MONATLICH, True))] = BooleanSelector()
    felder[
        vol.Optional(CONF_TAGE_MONATLICH, default=werte.get(CONF_TAGE_MONATLICH, DEFAULT_TAGE_MONATLICH))
    ] = TextSelector()
    return vol.Schema(felder)


def _pruefen(hass: HomeAssistant, eingabe: dict[str, Any]) -> dict[str, str]:
    fehler: dict[str, str] = {}
    eingabe[CONF_PERSONEN] = logic.personen_liste(eingabe.get(CONF_PERSONEN, []))
    aus_ha = ha_personen(hass) if eingabe.get(CONF_HA_PERSONEN) else []
    if not aus_ha and not eingabe[CONF_PERSONEN]:
        fehler[CONF_PERSONEN] = "keine_personen"
    for key in (CONF_TAGE, CONF_TAGE_MONATLICH) if eingabe.get(CONF_MONATLICH) else (CONF_TAGE,):
        try:
            if not logic.tage_liste(eingabe.get(key, "")):
                fehler[key] = "tage_ungueltig"
        except ValueError:
            fehler[key] = "tage_ungueltig"
    return fehler


class AboConfigFlow(ConfigFlow, domain=DOMAIN):
    """Neue Liste anlegen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            fehler = _pruefen(self.hass, user_input)
            if not fehler:
                name = user_input.pop(CONF_NAME).strip() or DEFAULT_NAME
                return self.async_create_entry(title=name, data={}, options=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, user_input or {}, mit_name=True),
            errors=fehler,
            description_placeholders={"ha_personen": ", ".join(ha_personen(self.hass)) or "–"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AboOptionsFlow()


class AboOptionsFlow(OptionsFlow):
    """Personen, Benachrichtigung und Erinnerungstage ändern."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            fehler = _pruefen(self.hass, user_input)
            if not fehler:
                return self.async_create_entry(data=user_input)
        werte = user_input or dict(self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(self.hass, werte, mit_name=False),
            errors=fehler,
            description_placeholders={"ha_personen": ", ".join(ha_personen(self.hass)) or "–"},
        )
