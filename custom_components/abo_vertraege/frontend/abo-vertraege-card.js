// Abos & Verträge – Karte zur Integration abo_vertraege.
// Liste mit Häkchen "gekündigt", Summe, Filter, Neu anlegen und Bearbeiten in der Zeile.
// Daten liegen in einer To-do-Liste; "completed" bedeutet hier "bereits gekündigt".
const ABO_ARTEN = ["Abo", "Verein", "Versicherung", "Strom/Gas", "Handy/Internet", "Haus", "Sonstiges"];
const ABO_ABR = { monatlich: 12, "vierteljährlich": 4, "halbjährlich": 2, "jährlich": 1 };
const ABO_VERL = ["Nein", "1 Monat", "3 Monate", "6 Monate", "12 Monate", "24 Monate"];
const NEU = "__neu__";

class AboVertraegeCard extends HTMLElement {
  static getStubConfig(hass) {
    const e = Object.keys(hass.states).find((id) => id.startsWith("todo.") && hass.states[id].attributes.abo_vertraege);
    return { entity: e || "todo.abos_vertrage" };
  }
  setConfig(config) {
    if (!config.entity) throw new Error("entity fehlt (todo-Liste von Abos & Verträge)");
    this._config = config;
    this._items = [];
    this._edit = null;
    this._filter = "Alle";
    this._filterArt = "Alle";
    this._sort = "Ende";
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    if (this._sub) this._unsubscribe();
    if (this._hass) this._subscribe();
  }
  set hass(hass) {
    const alt = this._personenText;
    this._hass = hass;
    this._personenText = JSON.stringify([this._personen, this._filterzeilen]);
    if (!this._sub) this._subscribe();
    else if (alt !== this._personenText) this._render();
  }
  get _filterzeilen() {
    // Aus den Einstellungen der Integration; in der Karte mit "filter: [...]" überschreibbar.
    if (this._config && Array.isArray(this._config.filter)) return this._config.filter;
    const st = this._hass && this._config && this._hass.states[this._config.entity];
    const z = st && st.attributes.filterzeilen;
    return Array.isArray(z) ? z : ["person", "art", "sortierung"];
  }
  get _personen() {
    if (this._config && this._config.personen) return this._config.personen;
    const st = this._hass && this._config && this._hass.states[this._config.entity];
    return (st && st.attributes.personen) || [];
  }
  connectedCallback() {
    if (this._hass && !this._sub) this._subscribe();
    this._render();
  }
  disconnectedCallback() {
    this._unsubscribe();
  }
  _unsubscribe() {
    if (this._sub) {
      this._sub.then((u) => u()).catch(() => {});
      this._sub = null;
    }
  }
  _subscribe() {
    if (!this.isConnected || !this._config) return;
    this._sub = this._hass.connection.subscribeMessage(
      (msg) => {
        this._items = msg.items || [];
        this._render();
      },
      { type: "todo/item/subscribe", entity_id: this._config.entity }
    );
    this._sub.catch(() => {
      this._error = `Liste ${this._config.entity} konnte nicht geladen werden`;
      this._render();
    });
  }
  _call(service, data) {
    return this._hass
      .callService("todo", service, data, { entity_id: this._config.entity })
      .catch((e) => {
        this._error = "Speichern fehlgeschlagen: " + (e.message || e);
        this._render();
      });
  }
  _days(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const a = new Date(y, m - 1, d);
    const n = new Date();
    return Math.round((a - new Date(n.getFullYear(), n.getMonth(), n.getDate())) / 86400000);
  }
  _fmt(iso) {
    const [y, m, d] = iso.split("-");
    return `${d}.${m}.${y}`;
  }
  _parse(item) {
    const seg = (item.description || "").split(" · ");
    const out = { art: "", preis: "", abr: "", frist: 0, einheit: "Tage", verl: "Nein", person: "", nk: false };
    seg.forEach((s, i) => {
      let r;
      if ((r = /^(\d+(?:,\d+)?) €$/.exec(s))) out.preis = r[1];
      else if (s in ABO_ABR) out.abr = s;
      else if (s === "nicht kündbar") out.nk = true;
      else if ((r = /^Kündigungsfrist (\d+) (Tage?|Monate?)$/.exec(s))) {
        out.frist = Number(r[1]);
        out.einheit = r[2].startsWith("Monat") ? "Monate" : "Tage";
      } else if ((r = /^verlängert um (.+)$/.exec(s))) out.verl = r[1];
      else if ((r = /^Person (.+)$/.exec(s))) out.person = r[1];
      else if (i === 0 && !/^kündigen bis/.test(s)) out.art = s;
    });
    return out;
  }
  _fristLabel(v) {
    return v.nk ? "nicht kündbar" : `Kündigungsfrist ${this._fristText(v)}`;
  }
  _fristText(v) {
    return `${v.frist} ${v.einheit === "Monate" ? (v.frist === 1 ? "Monat" : "Monate") : "Tage"}`;
  }
  _deadline(due, v) {
    if (v.nk) return null;
    const [y, m, d] = due.split("-").map(Number);
    const t = v.einheit === "Monate"
      ? new Date(y, m - 1 - v.frist, Math.min(d, new Date(y, m - v.frist, 0).getDate()))
      : new Date(y, m - 1, d - v.frist);
    const p = (x) => String(x).padStart(2, "0");
    return `${t.getFullYear()}-${p(t.getMonth() + 1)}-${p(t.getDate())}`;
  }
  _compose(v, due) {
    const parts = [];
    if (v.art) parts.push(v.art);
    if (v.preis) parts.push(`${v.preis} €`);
    if (v.abr) parts.push(v.abr);
    parts.push(this._fristLabel(v));
    if (v.verl !== "Nein") parts.push(`verlängert um ${v.verl}`);
    if (v.person) parts.push(`Person ${v.person}`);
    if (!v.nk) parts.push(`kündigen bis ${this._fmt(this._deadline(due, v))}`);
    return parts.join(" · ");
  }
  _status(item, v) {
    const done = item.status === "completed";
    if (!item.due) return { text: done ? "Gekündigt" : "Kein Datum", cls: done ? "ok" : "" };
    if (this._days(item.due) < 0) return { text: "Abgelaufen", cls: "" };
    if (done) return { text: `Gekündigt, läuft noch ${this._days(item.due)} Tage`, cls: "ok" };
    if (v.nk) {
      return v.verl !== "Nein"
        ? { text: `Verlängert sich am ${this._fmt(item.due)}`, cls: "" }
        : { text: `Nicht kündbar, läuft bis ${this._fmt(item.due)}`, cls: "" };
    }
    const rest = this._days(this._deadline(item.due, v));
    if (rest < 0) {
      return v.verl !== "Nein"
        ? { text: `Verlängert sich am ${this._fmt(item.due)}`, cls: "" }
        : { text: "Frist verpasst", cls: "bad" };
    }
    if (rest === 0) return { text: "Heute kündigen", cls: "bad" };
    return { text: `Noch ${rest} Tage zum Kündigen`, cls: rest <= 14 ? "bad" : rest <= 60 ? "warn" : "" };
  }
  _esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  _visible() {
    const z = this._filterzeilen;
    if (!z.includes("person")) this._filter = "Alle";
    if (!z.includes("art")) this._filterArt = "Alle";
    if (!z.includes("sortierung")) this._sort = "Ende";
    const person = this._filter === "Ohne Person" ? "" : this._filter;
    const art = this._filterArt === "Ohne Art" ? "" : this._filterArt;
    return this._items.filter((i) => {
      const v = this._parse(i);
      if (this._filter !== "Alle" && v.person !== person) return false;
      if (this._filterArt !== "Alle" && v.art !== art) return false;
      return true;
    });
  }
  _buttons(liste, aktiv, aktion) {
    return liste.map((n) => `<button class="${n === aktiv ? "primary" : ""}" data-a="${aktion}" data-f="${this._esc(n)}">${this._esc(n)}</button>`).join("");
  }
  _filterBar() {
    const ohne = this._items.some((i) => !this._parse(i).person);
    const namen = ["Alle", ...this._personen, ...(ohne ? ["Ohne Person"] : [])];
    const vorhanden = new Set(this._items.map((i) => this._parse(i).art));
    const extra = [...vorhanden].filter((a) => a && !ABO_ARTEN.includes(a)).sort();
    const arten = ["Alle", ...ABO_ARTEN, ...extra, ...(vorhanden.has("") ? ["Ohne Art"] : [])];
    const sortierung = ["Ende", "Kündigen bis", "Name", "Art", "Person", "Preis"];
    const z = this._filterzeilen;
    return (z.includes("person") ? `<div class="filter"><span class="flabel">Person</span>${this._buttons(namen, this._filter, "filter")}</div>` : "")
      + (z.includes("art") ? `<div class="filter"><span class="flabel">Art</span>${this._buttons(arten, this._filterArt, "filterArt")}</div>` : "")
      + (z.includes("sortierung") ? `<div class="filter"><span class="flabel">Sortiert</span>${this._buttons(sortierung, this._sort, "sort")}</div>` : "");
  }
  _jahr(v) {
    if (!v.preis || !v.abr) return 0;
    return parseFloat(v.preis.replace(",", ".")) * ABO_ABR[v.abr];
  }
  _sorted() {
    const ende = (i) => i.due || "9999";
    const frist = (i) => (i.due ? this._deadline(i.due, this._parse(i)) || "9999" : "9999");
    const name = (i) => (i.summary || "").toLowerCase();
    const txt = (a, b) => a.localeCompare(b, "de");
    const cmp = {
      Ende: (a, b) => txt(ende(a), ende(b)),
      "Kündigen bis": (a, b) => txt(frist(a), frist(b)) || txt(ende(a), ende(b)),
      Name: (a, b) => txt(name(a), name(b)),
      Art: (a, b) => txt(this._parse(a).art || "~", this._parse(b).art || "~") || txt(name(a), name(b)),
      Person: (a, b) => txt(this._parse(a).person || "~", this._parse(b).person || "~") || txt(name(a), name(b)),
      Preis: (a, b) => this._jahr(this._parse(b)) - this._jahr(this._parse(a)) || txt(name(a), name(b)),
    }[this._sort] || ((a, b) => txt(ende(a), ende(b)));
    return [...this._visible()].sort(cmp);
  }
  _euro(n) {
    return n.toFixed(2).replace(".", ",") + " €";
  }
  _summe() {
    let jahr = 0;
    let offen = 0;
    this._visible().forEach((i) => {
      if (i.status === "completed") return;
      if (i.due && this._days(i.due) < 0 && this._parse(i).verl === "Nein") return;
      const v = this._parse(i);
      if (!v.preis) return;
      if (!v.abr) {
        offen += 1;
        return;
      }
      jahr += parseFloat(v.preis.replace(",", ".")) * ABO_ABR[v.abr];
    });
    const hint = offen ? `<div class="info">${offen} ${offen === 1 ? "Eintrag" : "Einträge"} ohne Abrechnung nicht mitgezählt</div>` : "";
    return `<div class="sum"><div><div class="label">Pro Monat</div><div class="big">${this._euro(jahr / 12)}</div></div><div><div class="label">Pro Jahr</div><div class="big">${this._euro(jahr)}</div></div><div class="sumnote"><div class="info">Ohne gekündigte Einträge</div>${hint}</div></div>`;
  }
  _opts(list, cur) {
    const all = cur && !list.includes(cur) ? [cur, ...list] : list;
    return all.map((o) => `<option ${o === cur ? "selected" : ""}>${this._esc(o)}</option>`).join("");
  }
  _form(uid, name, due, v, neu) {
    const p = neu ? "n-" : "e-";
    return `<div class="edit">
      <label>Name<input id="${p}name" value="${this._esc(name)}"></label>
      <label>Person<select id="${p}person">${this._opts(["", ...this._personen], v.person)}</select></label>
      <label>Art<select id="${p}art">${this._opts(ABO_ARTEN, v.art)}</select></label>
      <label>Preis in €<input id="${p}preis" inputmode="decimal" size="8" value="${this._esc(v.preis)}"></label>
      <label>Abrechnung<select id="${p}abr">${this._opts(["", ...Object.keys(ABO_ABR)], v.abr)}</select></label>
      <label>Läuft bis<input id="${p}due" type="date" value="${this._esc(due || "")}"></label>
      <label>Frist<input id="${p}frist" class="frist" type="number" min="0" max="365" value="${v.frist}"></label>
      <label>Einheit<select id="${p}einheit">${this._opts(["Monate", "Tage", "nicht kündbar"], v.nk ? "nicht kündbar" : v.einheit)}</select></label>
      <label>Verlängert sich um<select id="${p}verl">${this._opts(ABO_VERL, v.verl)}</select></label>
      <button class="primary" data-a="save" data-u="${this._esc(uid)}">${neu ? "Eintrag speichern" : "Speichern"}</button>
      <button data-a="cancel" data-u="${this._esc(uid)}">${neu ? "Leeren" : "Abbrechen"}</button>
      ${neu ? "" : `<button class="danger" data-a="del" data-u="${this._esc(uid)}">Löschen</button>`}
    </div>`;
  }
  _heute() {
    const n = new Date();
    const p = (x) => String(x).padStart(2, "0");
    return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`;
  }
  _neuWerte() {
    // Eingaben im Formular "Neuer Eintrag" überleben jedes Neuzeichnen der Karte.
    const e = this._entwurf || {};
    const w = (k, std) => (e["n-" + k] !== undefined ? e["n-" + k] : std);
    return {
      name: w("name", ""), art: w("art", "Abo"), person: w("person", this._personen[0] || ""),
      preis: w("preis", "0"), abr: w("abr", "jährlich"), due: w("due", this._heute()),
      frist: w("frist", "0"), einheit: w("einheit", "Monate"), verl: w("verl", "Nein"),
    };
  }
  _feld(id, label, inhalt, art) {
    return `<label class="fld ${art || ""}">${label ? `<span class="lab">${label}</span>` : ""}${inhalt}</label>`;
  }
  _neuFormular() {
    const w = this._neuWerte();
    const ic = (i) => `<ha-icon class="ic" icon="${i}"></ha-icon>`;
    const sel = (id, liste, cur) => `<select id="n-${id}">${this._opts(liste, cur)}</select>`;
    return `<div class="neu">
      <div class="nhead"><ha-icon icon="mdi:plus-circle-outline"></ha-icon>Neuer Eintrag</div>
      <ha-card class="frm-card">${this._error ? `<div class="err">${this._esc(this._error)}</div>` : ""}<div class="frm">
        ${ic("mdi:form-textbox")}<div class="full">${this._feld("name", "Name", `<input id="n-name" placeholder="(leerer Wert)" value="${this._esc(w.name)}">`)}</div>
        ${ic("mdi:shape-outline")}<div>${this._feld("art", "Art", sel("art", ABO_ARTEN, w.art), "sel")}</div>
        ${ic("mdi:account")}<div>${this._feld("person", "Person", sel("person", ["", ...this._personen], w.person), "sel")}</div>
        ${ic("mdi:currency-eur")}<div class="inl"><span>Preis</span>${this._feld("preis", "", `<input id="n-preis" inputmode="decimal" class="num" value="${this._esc(w.preis)}"><span class="suf">€</span>`, "small")}</div>
        ${ic("mdi:cash-sync")}<div>${this._feld("abr", "Abrechnung", sel("abr", ["", ...Object.keys(ABO_ABR)], w.abr), "sel")}</div>
        ${ic("mdi:calendar-end")}<div class="full inl"><span>Laufzeitende</span>${this._feld("due", "", `<input id="n-due" type="date" value="${this._esc(w.due)}">`, "wide")}</div>
        ${ic("mdi:calendar-clock")}<div class="inl"><span>Frist</span>${this._feld("frist", "", `<input id="n-frist" type="number" min="0" max="365" class="num" value="${this._esc(w.frist)}">`, "small")}</div>
        ${ic("mdi:calendar-range")}<div>${this._feld("einheit", "Einheit", sel("einheit", ["Monate", "Tage", "nicht kündbar"], w.einheit), "sel")}</div>
        ${ic("mdi:calendar-sync")}<div class="full">${this._feld("verl", "Verlängert sich um", sel("verl", ABO_VERL, w.verl), "sel")}</div>
      </div></ha-card>
      <ha-card class="btn-card" data-a="save" data-u="${NEU}" role="button" tabindex="0"><ha-icon icon="mdi:content-save"></ha-icon>Eintrag speichern</ha-card>
    </div>`;
  }
  _row(item) {
    const uid = this._esc(item.uid);
    const v = this._parse(item);
    const s = this._status(item, v);
    const done = item.status === "completed";
    const info = [v.art, this._fristLabel(v), v.verl !== "Nein" ? `verlängert sich um ${v.verl}` : ""].filter(Boolean).join(" · ");
    const main = `<div class="row ${done ? "done" : ""}">
      <label class="check" title="Bereits gekündigt"><input type="checkbox" data-a="toggle" data-u="${uid}" ${done ? "checked" : ""}><span>gekündigt</span></label>
      <div class="main"><div class="name">${this._esc(item.summary)}</div><div class="info">${v.person ? `<b class="pers">${this._esc(v.person)}</b>${info ? " · " : ""}` : ""}${this._esc(info)}</div></div>
      <div class="date"><div class="label">Preis</div><div>${v.preis ? this._esc(v.preis) + " €" : "–"}</div><div class="info">${this._esc(v.abr)}</div></div>
      <div class="date"><div class="label">Läuft bis</div><div>${item.due ? this._fmt(item.due) : "–"}</div></div>
      <div class="date"><div class="label">Kündigen bis</div><div>${item.due && !v.nk ? this._fmt(this._deadline(item.due, v)) : "–"}</div></div>
      <div class="status ${s.cls}">${this._esc(s.text)}</div>
      <button data-a="edit" data-u="${uid}" aria-label="Bearbeiten">Ändern</button>
    </div>`;
    if (this._edit !== item.uid) return main;
    return main + this._form(item.uid, item.summary, item.due, v, false);
  }
  _render() {
    if (!this.shadowRoot || !this._config) return;
    const fz = this._filterzeilen;
    if (!fz.includes("person")) this._filter = "Alle";
    if (!fz.includes("art")) this._filterArt = "Alle";
    if (!fz.includes("sortierung")) this._sort = "Ende";
    const active = this.shadowRoot.activeElement;
    if (active && (active.tagName === "SELECT" || (active.tagName === "INPUT" && active.type !== "checkbox"))) return;
    const rows = this._sorted().map((i) => this._row(i)).join("");
    const titelHtml = this._config.title ? `<div class="title">${this._esc(this._config.title)}</div>` : "";
    const teil = this._config.teil || "beide";
    const neu = teil === "liste" ? "" : this._neuFormular();
    const liste = teil === "formular" ? "" : `<ha-card class="liste">${titelHtml}${this._error && teil === "liste" ? `<div class="err">${this._esc(this._error)}</div>` : ""}${this._filterBar()}${this._summe()}${rows || `<div class="empty">Noch keine Einträge</div>`}</ha-card>`;
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}
      .liste{padding:12px 16px}
      .neu{display:flex;flex-direction:column;gap:12px;margin-bottom:12px}
      .nhead{display:flex;align-items:center;gap:8px;font-size:16px;font-weight:500;padding:4px 4px 0}
      .frm{display:grid;grid-template-columns:28px minmax(0,1fr) 28px minmax(0,1fr);gap:22px 14px;align-items:center;padding:16px}
      .frm .full{grid-column:2/5}
      .ic{color:var(--state-icon-color,#44739e)}
      .inl{display:flex;align-items:center;gap:12px}.inl>span{flex:1;white-space:nowrap}
      .fld{position:relative;display:flex;flex-direction:column;justify-content:center;box-sizing:border-box;min-height:56px;padding:6px 12px 4px;background:var(--input-fill-color,rgba(127,127,127,.1));border-radius:4px 4px 0 0;border-bottom:1px solid var(--input-idle-line-color,rgba(127,127,127,.6));cursor:text}
      .fld:focus-within{border-bottom:2px solid var(--primary-color)}
      .fld .lab{font-size:11px;color:var(--secondary-text-color)}
      .fld:focus-within .lab{color:var(--primary-color)}
      .fld input,.fld select{border:none;outline:none;background:transparent;font:inherit;font-size:16px;color:var(--primary-text-color);padding:2px 0;width:100%;min-width:0;-webkit-appearance:none;appearance:none}
      .fld input::placeholder{color:var(--secondary-text-color)}
      .fld.sel{cursor:pointer}.fld.sel::after{content:"";position:absolute;right:14px;top:50%;border:5px solid transparent;border-top-color:var(--secondary-text-color);margin-top:-2px;pointer-events:none}
      .fld.sel select{padding-right:22px;cursor:pointer}.fld select option{color:#111;background:#fff}
      .fld.small{width:100px;flex:0 0 100px;flex-direction:row;align-items:center}.fld .num{text-align:center}.suf{color:var(--secondary-text-color);font-size:14px;padding-left:4px}
      .fld.wide{flex:0 0 min(230px,60%)}
      .fld input[type=date]::-webkit-calendar-picker-indicator{opacity:.7;cursor:pointer}
      .btn-card{display:flex;align-items:center;gap:16px;padding:16px;font-weight:500;cursor:pointer}
      .btn-card ha-icon{color:var(--state-icon-color,#44739e)}
      .btn-card:hover{background:rgba(127,127,127,.08)}
      .frm-card .err{padding:12px 16px 0}
      @media(max-width:420px){.frm{grid-template-columns:28px minmax(0,1fr)}.frm .full{grid-column:2/3}}
      .title{font-size:20px;font-weight:500;padding:4px 0 12px}
      .row{display:grid;grid-template-columns:auto minmax(120px,1fr) 88px 92px 92px minmax(120px,170px) auto;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--divider-color)}
      .check{display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px;color:var(--secondary-text-color);cursor:pointer}
      .check input{width:22px;height:22px;margin:0;cursor:pointer;accent-color:var(--success-color,#2e7d32)}
      .name{font-weight:700;font-size:15px;overflow-wrap:anywhere}.pers{font-weight:700}
      .info,.label{font-size:12px;color:var(--secondary-text-color)}
      .date{font-size:14px;white-space:nowrap}
      .status{font-size:13px}.ok{color:var(--success-color,#2e7d32)}.warn{color:var(--warning-color,#b26a00)}.bad{color:var(--error-color,#c62828);font-weight:500}
      .filter{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:0 0 8px}.flabel{font-size:12px;color:var(--secondary-text-color);width:56px}
      .sum{display:flex;flex-wrap:wrap;gap:24px;align-items:center;padding:4px 0 12px}.big{font-size:20px;font-weight:500}.sumnote{flex:1;min-width:150px}
      .newbox{border-bottom:1px solid var(--divider-color);margin-bottom:12px}.head{font-weight:500;font-size:16px}
      button{font:inherit;font-size:13px;padding:6px 10px;border:1px solid var(--divider-color);border-radius:8px;background:transparent;color:var(--primary-text-color);cursor:pointer}
      .primary{background:var(--primary-color);border-color:var(--primary-color);color:var(--text-primary-color,#fff)}
      .danger{color:var(--error-color,#c62828);margin-left:auto}
      .edit{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;padding:8px 0 12px}
      .edit label{display:flex;flex-direction:column;font-size:12px;color:var(--secondary-text-color);gap:3px}
      .edit input,.edit select{font:inherit;font-size:14px;padding:6px;border:1px solid var(--divider-color);border-radius:6px;background:transparent;color:var(--primary-text-color)}
      .edit select option{color:#111;background:#fff}
      .frist{width:70px}
      .empty,.err{padding:16px 0;color:var(--secondary-text-color)}.err{color:var(--error-color,#c62828)}
      @media(max-width:700px){.row{grid-template-columns:auto 1fr auto}.date,.status{grid-column:2/4}.date{display:flex;gap:8px}}
    </style>${neu}${liste}`;
    this.shadowRoot.querySelectorAll('[id^="n-"]').forEach((el) => {
      const merken = () => {
        this._entwurf = { ...(this._entwurf || {}), [el.id]: el.value };
      };
      el.addEventListener("input", merken);
      el.addEventListener("change", merken);
    });
    this.shadowRoot.querySelectorAll("[data-a]").forEach((el) => {
      el.addEventListener(el.type === "checkbox" ? "change" : "click", (ev) => this._action(ev.currentTarget));
    });
  }
  _action(el) {
    const a = el.dataset.a;
    const item = this._items.find((i) => i.uid === el.dataset.u);
    const p = el.dataset.u === NEU ? "n-" : "e-";
    const q = (id) => this.shadowRoot.getElementById(p + id.slice(2)).value;
    const blur = () => this.shadowRoot.activeElement && this.shadowRoot.activeElement.blur();
    this._error = null;
    if (a === "filter" || a === "filterArt" || a === "sort") {
      if (a === "filter") this._filter = el.dataset.f;
      else if (a === "filterArt") this._filterArt = el.dataset.f;
      else this._sort = el.dataset.f;
      this._edit = null;
      this._render();
    } else if (a === "toggle" && item) {
      this._call("update_item", { item: item.uid, status: el.checked ? "completed" : "needs_action" });
    } else if (a === "new") {
      this._edit = this._edit === NEU ? null : NEU;
      this._render();
    } else if (a === "edit") {
      this._edit = this._edit === el.dataset.u ? null : el.dataset.u;
      this._render();
    } else if (a === "cancel") {
      if (el.dataset.u === NEU) this._entwurf = null;
      this._edit = null;
      blur();
      this._render();
    } else if (a === "save" && (item || el.dataset.u === NEU)) {
      const name = q("e-name").trim();
      const due = q("e-due");
      const preisText = q("e-preis").trim().replace(/[€\s]/g, "");
      const zahl = parseFloat(preisText.replace(",", "."));
      const frist = parseInt(q("e-frist"), 10);
      if (!name || !due || Number.isNaN(frist) || frist < 0 || (preisText && Number.isNaN(zahl))) {
        this._error = "Bitte Name, Datum, Frist und Preis prüfen";
        this._render();
        return;
      }
      const einheit = q("e-einheit");
      const v = { art: q("e-art"), preis: preisText ? zahl.toFixed(2).replace(".", ",") : "", abr: q("e-abr"), frist, einheit: einheit === "nicht kündbar" ? "Tage" : einheit, verl: q("e-verl"), person: q("e-person"), nk: einheit === "nicht kündbar" };
      this._edit = null;
      if (!item) this._entwurf = null;
      blur();
      if (item) this._call("update_item", { item: item.uid, rename: name, due_date: due, description: this._compose(v, due) });
      else this._call("add_item", { item: name, due_date: due, description: this._compose(v, due) });
      this._render();
    } else if (a === "del" && item) {
      if (el.dataset.sure) {
        this._edit = null;
        this._call("remove_item", { item: item.uid });
      } else {
        el.dataset.sure = "1";
        el.textContent = "Wirklich löschen?";
      }
    }
  }
  getCardSize() {
    return 3 + this._items.length;
  }
  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }
}
if (!customElements.get("abo-vertraege-card")) customElements.define("abo-vertraege-card", AboVertraegeCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "abo-vertraege-card", name: "Abos & Verträge", description: "Abos und Verträge mit Kündigungsfristen, Summe und Erinnerung", preview: false });
