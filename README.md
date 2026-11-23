<p align="center">
  <img src="custom_components/abo_vertraege/brand/icon@2x.png" alt="Abos & Verträge" width="128">
</p>

<h1 align="center">Abos & Verträge</h1>

<p align="center">
  Abos, Verträge, Versicherungen und Beiträge in Home Assistant verwalten – mit Kündigungsfristen, Kostenübersicht und rechtzeitiger Erinnerung.
</p>

---

## Was die Integration macht

Wer kennt es nicht: Das Streaming-Abo, das man eigentlich kündigen wollte, hat sich gerade wieder um ein Jahr verlängert. **Abos & Verträge** behält alle laufenden Verträge im Blick und meldet sich, **bevor** die Kündigungsfrist abläuft.

- **Alles an einem Ort** – Streaming, Handy, Internet, Strom, Versicherungen, Vereinsbeiträge, Gebühren rund ums Haus
- **Kündigungsfrist richtig berechnet** – in Tagen oder Monaten (auch bei Monatsenden wie 31.03. → 28.02.), oder „nicht kündbar“
- **Automatische Verlängerung** – läuft ein Vertrag ab und verlängert sich (1, 3, 6, 12 oder 24 Monate), setzt die Integration Laufzeitende und letzten Kündigungstag selbst weiter
- **Erinnerungen** aufs Handy oder in Home Assistant, an frei wählbaren Tagen vor dem letzten Kündigungstag
- **Monats-Abos** wie Disney+ oder Netflix bekommen eine eigene, kurze Erinnerung (Standard 7 Tage vorher) – abschaltbar
- **Kostenübersicht** – Summe pro Monat und pro Jahr, wahlweise gefiltert nach Person oder Art
- **Für die ganze Familie** – Personen werden automatisch aus Home Assistant übernommen, weitere Namen wie „Gemeinsam“ lassen sich ergänzen
- **Eigene Karte inklusive** – Formular für neue Einträge, Liste mit Status, Häkchen „gekündigt“, Bearbeiten und Löschen direkt in der Zeile
- **Keine Helfer, Skripte oder Automationen nötig** – einfach installieren, einrichten, Karte hinzufügen

<!-- Screenshot einfügen, z. B.:
<p align="center"><img src="docs/karte.png" alt="Karte Abos & Verträge" width="800"></p>
-->

## Voraussetzungen

- Home Assistant **2026.3** oder neuer
- Für Erinnerungen aufs Handy: die Home Assistant Companion App (oder ein anderer Benachrichtigungsdienst wie Pushover, Telegram …)

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → oben rechts **⋮** → **Benutzerdefinierte Repositories**
2. URL dieses Repositorys eintragen, Typ **Integration** → **Hinzufügen**
3. **Abos & Verträge** suchen und **Herunterladen**
4. Home Assistant **neu starten**

### Manuell

1. Den Ordner `custom_components/abo_vertraege` aus diesem Repository nach `/config/custom_components/abo_vertraege` kopieren (z. B. per Samba-Freigabe oder Studio Code Server)
2. Home Assistant **neu starten**

## Einrichtung

**Einstellungen → Geräte & Dienste → Integration hinzufügen → „Abos & Verträge“**

Es erscheint ein Dialog mit den unten beschriebenen Einstellungen. Danach gibt es eine neue To-do-Liste, z. B. `todo.abos_vertrage`, in der alle Einträge gespeichert werden.

Alle Einstellungen außer dem Namen lassen sich später ändern unter **Einstellungen → Geräte & Dienste → Abos & Verträge → Konfigurieren**.

Mehrere Listen sind möglich (z. B. eine private und eine für den Verein) – einfach die Integration ein weiteres Mal hinzufügen.

## Die Einstellungen im Einzelnen

| Einstellung | Wofür sie da ist | Standard |
|---|---|---|
| **Name der Liste** | Name der To-do-Liste und damit auch ihrer Entity-ID (z. B. „Abos & Verträge“ → `todo.abos_vertrage`). Nur bei der Einrichtung wählbar. | Abos & Verträge |
| **Personen aus Home Assistant übernehmen** | Die **Vornamen** aller unter *Einstellungen → Personen* angelegten Personen stehen in der Karte zur Auswahl („Max Mustermann“ → „Max“). Wird später jemand angelegt, umbenannt oder gelöscht, passt sich die Auswahl von selbst an. | an |
| **Weitere Personen** | Zusätzliche Namen für die Auswahl, z. B. „Gemeinsam“ oder Kinder ohne eigene Person in Home Assistant. Namen eintippen und mit Enter bestätigen. Doppelte Namen erscheinen nur einmal. | Gemeinsam |
| **Filterzeilen in der Karte** | Welche Zeilen über der Liste angezeigt werden: **Person** (nur Einträge einer Person zeigen), **Art** (z. B. nur Versicherungen), **Sortiert** (Reihenfolge ändern). Ausgeblendete Zeilen werden auf „Alle“ bzw. „nach Ende sortiert“ zurückgesetzt. | alle drei |
| **Benachrichtigen an** | Wohin die Erinnerungen geschickt werden – eine oder mehrere Benachrichtigungs-Entitäten oder -Aktionen, z. B. `notify.mobile_app_mein_handy`. **Leer lassen:** Die Erinnerung erscheint unter *Benachrichtigungen* in Home Assistant. | leer |
| **Uhrzeit der Erinnerung** | Wann täglich geprüft und erinnert wird. | 09:00 |
| **Erinnern … Tage vor dem letzten Kündigungstag** | An welchen Tagen vor dem letzten Kündigungstag eine Erinnerung kommt, durch Komma getrennt. `0` = am letzten Tag selbst. Gilt für alle Einträge, die sich **nicht** monatlich verlängern. | 60, 30, 14, 7, 1, 0 |
| **Erinnerung bei monatlicher Verlängerung** | Schalter für Abos, die sich **jeden Monat** verlängern (Disney+, Netflix, Spotify …). Bei diesen wären 60 oder 30 Tage Vorlauf sinnlos – sie haben deshalb eine eigene Einstellung. Aus = für Monats-Abos keine Erinnerung. | an |
| **Bei monatlicher Verlängerung … Tage vorher erinnern** | Wie viele Tage vor dem letzten Kündigungstag Monats-Abos erinnert werden. Mehrere Werte möglich, z. B. `7, 1`. | 7 |

## Die Karte

Die Karte wird von der Integration selbst bereitgestellt – eine Ressource unter *Dashboards* ist **nicht** nötig.

Dashboard bearbeiten → **Karte hinzufügen** → nach „Abos & Verträge“ suchen, oder im Code-Editor:

```yaml
type: custom:abo-vertraege-card
entity: todo.abos_vertrage
```

Sie besteht aus zwei Teilen:

- **Neuer Eintrag** – Formular mit Name, Art, Person, Preis, Abrechnung, Laufzeitende, Kündigungsfrist und Verlängerung, darunter „Eintrag speichern“
- **Liste** – Summe pro Monat und Jahr, Filterzeilen, alle Einträge mit Status (z. B. „Noch 23 Tage zum Kündigen“, „Heute kündigen“, „Verlängert sich am …“), Häkchen **gekündigt** und Knopf **Ändern** zum Bearbeiten oder Löschen

### Optionen der Karte

| Option | Bedeutung |
|---|---|
| `entity` | **Pflicht.** Die To-do-Liste der Integration. |
| `teil` | `formular` = nur das Formular, `liste` = nur die Liste. Ohne Angabe stehen beide untereinander. Praktisch für ein Layout mit Formular links und Liste rechts (zwei Karten). |
| `filter` | Überschreibt für diese Karte die Filterzeilen aus den Einstellungen, z. B. `filter: [person, sortierung]`. |
| `personen` | Überschreibt für diese Karte die Personenauswahl, z. B. `personen: [Max, Erika, Gemeinsam]`. |
| `title` | Überschrift über der Liste. |

Beispiel für zwei Spalten in einer Abschnittsansicht:

```yaml
# linke Spalte
type: custom:abo-vertraege-card
entity: todo.abos_vertrage
teil: formular
```

```yaml
# rechte Spalte (Abschnitt doppelt breit)
type: custom:abo-vertraege-card
entity: todo.abos_vertrage
teil: liste
```

## Die Felder eines Eintrags

| Feld | Bedeutung |
|---|---|
| **Name** | Bezeichnung, z. B. „Netflix“ oder „Kfz-Versicherung“ |
| **Art** | Abo, Verein, Versicherung, Strom/Gas, Handy/Internet, Haus, Sonstiges – für Filter und Übersicht |
| **Person** | Wem der Vertrag gehört – steht auch im Titel der Erinnerung |
| **Preis** + **Abrechnung** | Betrag pro Abrechnungszeitraum (monatlich, vierteljährlich, halbjährlich, jährlich). Daraus entsteht die Summe pro Monat und Jahr. |
| **Laufzeitende** | Bis wann der Vertrag aktuell läuft |
| **Frist** + **Einheit** | Kündigungsfrist in Monaten oder Tagen – oder **nicht kündbar** (z. B. Grundsteuer, Rundfunkbeitrag): dann gibt es keinen Kündigungstag und keine Erinnerung |
| **Verlängert sich um** | Ob und um wie viel sich der Vertrag nach Laufzeitende automatisch verlängert: Nein, 1, 3, 6, 12 oder 24 Monate |

Aus Laufzeitende und Frist berechnet die Integration den **letzten Kündigungstag**.

## So arbeitet die Integration im Hintergrund

- **Jede Nacht (00:10)** und beim Start von Home Assistant: Einträge, deren Laufzeitende vorbei ist und die sich verlängern, bekommen ein neues Laufzeitende und einen neuen letzten Kündigungstag.
- **Täglich zur eingestellten Uhrzeit:** Für jeden offenen Eintrag wird geprüft, ob heute einer der Erinnerungstage ist. Wenn ja, kommt eine Nachricht wie
  > **Kündigung prüfen (Max)**
  > Netflix: noch 7 Tage bis zum letzten Kündigungstag (08.12.2026). Laufzeitende: 15.12.2026. 13,99 € monatlich.
- **Gekündigte Einträge** (Häkchen gesetzt) werden weder verlängert noch erinnert. Sie bleiben sichtbar, bis das Laufzeitende erreicht ist („Gekündigt, läuft noch 12 Tage“), und zählen nicht mehr in die Summe.
- **Abgelaufene Einträge ohne Verlängerung** bleiben als „Abgelaufen“ stehen, bis du sie löschst.

## Aktionen

| Aktion | Wofür |
|---|---|
| `abo_vertraege.importieren` | Übernimmt Einträge aus einer anderen To-do-Liste im gleichen Format (z. B. beim Umzug von einer selbst gebauten Lösung). Doppelte Einträge (gleicher Name und gleiches Laufzeitende) werden übersprungen. |
| `abo_vertraege.jetzt_pruefen` | Führt Verlängerung und Erinnerung sofort aus – praktisch zum Testen der Benachrichtigung. |

## Wo die Daten liegen

Jeder Eintrag ist ein ganz normaler Eintrag der To-do-Liste:

- **Name** = Bezeichnung
- **Fälligkeitsdatum** = Laufzeitende
- **Erledigt** = bereits gekündigt
- **Beschreibung** = alle übrigen Angaben, lesbar, z. B.
  `Abo · 13,99 € · monatlich · Kündigungsfrist 7 Tage · verlängert um 1 Monat · Person Max · kündigen bis 08.12.2026`

Damit erscheinen die Einträge auch im normalen To-do-Bereich von Home Assistant, und eigene Automationen können sie mit `todo.get_items` auslesen.

Gespeichert wird alles lokal in Home Assistant (`/config/.storage/`) und ist in jedem Home-Assistant-Backup enthalten. Es werden keine Daten an Dritte geschickt.

## Häufige Fragen

**Die Karte erscheint nicht in der Kartenauswahl.**
Nach Installation oder Update Home Assistant neu starten und die Seite mit Strg+F5 neu laden. In der Companion App: *Einstellungen → Companion App → Frontend-Cache zurücksetzen*.

**Es kommen keine Erinnerungen.**
Unter *Konfigurieren* prüfen, ob ein Benachrichtigungsziel gewählt ist, und mit der Aktion `abo_vertraege.jetzt_pruefen` testen. Ohne Ziel landen die Erinnerungen unter *Benachrichtigungen* in Home Assistant. Erinnert wird nur an den eingestellten Tagen – nicht an jedem Tag dazwischen.

**Eine Person fehlt in der Auswahl.**
Entweder unter *Einstellungen → Personen* anlegen (wird automatisch übernommen) oder unter *Konfigurieren → Weitere Personen* eintragen.

**Kann ich die Integration wieder entfernen?**
Ja. Beim Entfernen der Integration werden auch die gespeicherten Einträge gelöscht – vorher ggf. mit `todo.get_items` sichern oder ein Backup machen.

## Hinweis

Dies ist eine private, nicht offizielle Integration ohne Verbindung zu Home Assistant oder Nabu Casa. Die berechneten Kündigungstage ersetzen nicht den Blick in den jeweiligen Vertrag – maßgeblich sind immer die Vertragsbedingungen des Anbieters.
