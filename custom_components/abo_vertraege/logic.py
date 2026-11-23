"""Reine Rechenlogik (ohne Home Assistant), damit sie testbar bleibt.

Die Daten eines Eintrags stehen wie in der Karte in der Beschreibung des
To-do-Eintrags, Teile getrennt durch " · ", zum Beispiel:
"Abo · 12,99 € · monatlich · Kündigungsfrist 1 Monat · verlängert um 1 Monat ·
Person Anna · kündigen bis 30.11.2026"
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

ABRECHNUNG = {"monatlich": 12, "vierteljährlich": 4, "halbjährlich": 2, "jährlich": 1}
TRENNER = " · "

_RE_PREIS = re.compile(r"^(\d+(?:,\d+)?) €$")
_RE_FRIST = re.compile(r"^Kündigungsfrist (\d+) (Tage?|Monate?)$")
_RE_VERL = re.compile(r"^verlängert um (.+)$")
_RE_PERSON = re.compile(r"^Person (.+)$")
_RE_MONATE = re.compile(r"^(\d+) Monat")


@dataclass
class Eintrag:
    """Die Felder aus der Beschreibung."""

    art: str = ""
    preis: str = ""
    abrechnung: str = ""
    frist: int = 0
    einheit: str = "Tage"
    verlaengerung: str = "Nein"
    person: str = ""
    nicht_kuendbar: bool = False

    @property
    def monate(self) -> int:
        """Verlängerung in Monaten, 0 = keine."""
        treffer = _RE_MONATE.match(self.verlaengerung or "")
        return int(treffer.group(1)) if treffer else 0


def parse(beschreibung: str | None) -> Eintrag:
    """Beschreibung in Felder zerlegen (wie _parse in der Karte)."""
    e = Eintrag()
    for i, teil in enumerate((beschreibung or "").split(TRENNER)):
        if m := _RE_PREIS.match(teil):
            e.preis = m.group(1)
        elif teil in ABRECHNUNG:
            e.abrechnung = teil
        elif teil == "nicht kündbar":
            e.nicht_kuendbar = True
        elif m := _RE_FRIST.match(teil):
            e.frist = int(m.group(1))
            e.einheit = "Monate" if m.group(2).startswith("Monat") else "Tage"
        elif m := _RE_VERL.match(teil):
            e.verlaengerung = m.group(1)
        elif m := _RE_PERSON.match(teil):
            e.person = m.group(1)
        elif i == 0 and not teil.startswith("kündigen bis"):
            e.art = teil
    return e


def monate_addieren(start: date, monate: int, tag: int | None = None) -> date:
    """Monate addieren (auch negativ); der Tag wird aufs Monatsende begrenzt."""
    gesamt = start.year * 12 + (start.month - 1) + monate
    jahr, monat0 = divmod(gesamt, 12)
    letzter = calendar.monthrange(jahr, monat0 + 1)[1]
    return date(jahr, monat0 + 1, min(tag or start.day, letzter))


def letzter_kuendigungstag(ende: date, e: Eintrag) -> date | None:
    """Letzter Tag, an dem noch gekündigt werden kann; None bei nicht kündbar."""
    if e.nicht_kuendbar:
        return None
    if e.einheit == "Monate":
        return monate_addieren(ende, -e.frist)
    return date.fromordinal(ende.toordinal() - e.frist)


def frist_text(e: Eintrag) -> str:
    """Text der Kündigungsfrist."""
    if e.nicht_kuendbar:
        return "nicht kündbar"
    if e.einheit == "Monate":
        return f"Kündigungsfrist {e.frist} {'Monat' if e.frist == 1 else 'Monate'}"
    return f"Kündigungsfrist {e.frist} Tage"


def compose(e: Eintrag, ende: date) -> str:
    """Beschreibung aus den Feldern bauen (wie _compose in der Karte)."""
    teile = []
    if e.art:
        teile.append(e.art)
    if e.preis:
        teile.append(f"{e.preis} €")
    if e.abrechnung:
        teile.append(e.abrechnung)
    teile.append(frist_text(e))
    if e.verlaengerung and e.verlaengerung != "Nein":
        teile.append(f"verlängert um {e.verlaengerung}")
    if e.person:
        teile.append(f"Person {e.person}")
    bis = letzter_kuendigungstag(ende, e)
    if bis:
        teile.append(f"kündigen bis {bis:%d.%m.%Y}")
    return TRENNER.join(teile)


def neues_ende(ende: date, monate: int, heute: date) -> date | None:
    """Laufzeitende so oft um `monate` verschieben, bis es nicht mehr vorbei ist."""
    if monate <= 0 or ende >= heute:
        return None
    schritt = 1
    while schritt <= 600:
        kandidat = monate_addieren(ende, monate * schritt, ende.day)
        if kandidat >= heute:
            return kandidat
        schritt += 1
    return None


def tage_liste(text: str) -> list[int]:
    """'60, 30, 7' -> [60, 30, 7]; wirft ValueError bei Unsinn."""
    werte = [int(t) for t in re.split(r"[,;\s]+", text or "") if t.strip()]
    if any(w < 0 or w > 365 for w in werte):
        raise ValueError("Tage zwischen 0 und 365")
    return sorted(set(werte), reverse=True)


def vorname(name: str) -> str:
    """'Anna Muster' -> 'Anna'."""
    teile = str(name or "").split()
    return teile[0] if teile else ""


def personen_liste(wert) -> list[str]:
    """Liste oder Text 'Anna, Ben' -> ['Anna', 'Ben'], ohne Doppelte."""
    teile = wert if isinstance(wert, (list, tuple)) else str(wert or "").split(",")
    out: list[str] = []
    for p in teile:
        p = str(p).strip()
        if p and p not in out:
            out.append(p)
    return out


def erinnerung(
    titel: str,
    ende: date,
    e: Eintrag,
    heute: date,
    tage: list[int],
    tage_monatlich: list[int] | None = None,
) -> tuple[str, str] | None:
    """Titel und Text einer Erinnerung, wenn heute eine fällig ist, sonst None.

    Verlängert sich ein Eintrag jeden Monat, gelten nur `tage_monatlich`
    (leer oder None = keine Erinnerung für monatliche Abos).
    """
    bis = letzter_kuendigungstag(ende, e)
    if bis is None:
        return None
    rest = bis.toordinal() - heute.toordinal()
    if rest not in ((tage_monatlich or []) if e.monate == 1 else tage):
        return None
    if rest == 0:
        wann = "heute ist der letzte Kündigungstag"
    elif rest == 1:
        wann = "morgen ist der letzte Kündigungstag"
    else:
        wann = f"noch {rest} Tage bis zum letzten Kündigungstag"
    kopf = "Kündigung prüfen" + (f" ({e.person})" if e.person else "")
    text = f"{titel}: {wann} ({bis:%d.%m.%Y}). Laufzeitende: {ende:%d.%m.%Y}."
    if e.preis:
        text += f" {e.preis} €" + (f" {e.abrechnung}" if e.abrechnung else "") + "."
    return kopf, text
