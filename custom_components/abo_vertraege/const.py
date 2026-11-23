"""Konstanten für Abos & Verträge."""

DOMAIN = "abo_vertraege"
VERSION = "1.0.6"

CONF_NAME = "name"
CONF_PERSONEN = "personen"  # zusätzliche Personen (Liste)
CONF_HA_PERSONEN = "ha_personen"  # Personen aus Home Assistant übernehmen
CONF_NOTIFY = "benachrichtigen"
CONF_TAGE = "erinnerung_tage"
# Abos, die sich jeden Monat verlängern (Disney+, Netflix …): eigene Erinnerung, abschaltbar
CONF_MONATLICH = "erinnerung_monatlich"
CONF_TAGE_MONATLICH = "erinnerung_tage_monatlich"
CONF_ZEIT = "erinnerung_zeit"
CONF_FILTER = "filterzeilen"  # welche Zeilen die Karte über der Liste zeigt
FILTER_ZEILEN = ["person", "art", "sortierung"]

DEFAULT_NAME = "Abos & Verträge"
DEFAULT_PERSONEN = ["Gemeinsam"]
DEFAULT_TAGE = "60, 30, 14, 7, 1, 0"
DEFAULT_TAGE_MONATLICH = "7"
DEFAULT_ZEIT = "09:00:00"

CARD_URL = f"/{DOMAIN}/abo-vertraege-card.js"

SERVICE_IMPORT = "importieren"
SERVICE_PRUEFEN = "jetzt_pruefen"
