#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
import argparse
import re


@dataclass(frozen=True)
class Row:
    paper: str
    conference: str
    conference_link: str
    location: str
    date_raw: str
    presenter: str
    role: str
    registration: str
    hotel: str
    flight: str
    start: date | None
    end: date | None


def _parse_date_range(value: str) -> tuple[date | None, date | None]:
    value = (value or "").strip()
    if not value:
        return (None, None)
    if " to " in value:
        start_s, end_s = [p.strip() for p in value.split(" to ", 1)]
    else:
        start_s, end_s = value, value
    return (date.fromisoformat(start_s), date.fromisoformat(end_s))


def _status_kind(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"yes", "y", "true", "1"}:
        return "yes"
    if v in {"no", "n", "false", "0"}:
        return "no"
    if v in {"n/a", "na"}:
        return "na"
    return "tbd"


def _read_rows(csv_path: Path) -> list[Row]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "Paper",
            "Conference",
            "Conference Link",
            "Location",
            "Date",
            "Presenter",
            "Role",
            "Registration",
            "Hotel",
            "Flight",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")

        rows: list[Row] = []
        for i, r in enumerate(reader, start=2):
            start, end = _parse_date_range(r["Date"])
            try:
                rows.append(
                    Row(
                        paper=(r["Paper"] or "").strip(),
                        conference=(r["Conference"] or "").strip(),
                        conference_link=(r["Conference Link"] or "").strip(),
                        location=(r["Location"] or "").strip(),
                        date_raw=(r["Date"] or "").strip(),
                        presenter=(r["Presenter"] or "").strip(),
                        role=(r["Role"] or "").strip(),
                        registration=(r["Registration"] or "").strip(),
                        hotel=(r["Hotel"] or "").strip(),
                        flight=(r["Flight"] or "").strip(),
                        start=start,
                        end=end,
                    )
                )
            except Exception as e:  # noqa: BLE001
                raise ValueError(f"Row {i}: {e}") from e
        return rows


def _row_to_dict(r: Row) -> dict[str, Any]:
    return {
        "paper": r.paper,
        "conference": r.conference,
        "conferenceLink": r.conference_link,
        "location": r.location,
        "dateRaw": r.date_raw,
        "presenter": r.presenter,
        "role": r.role,
        "registration": r.registration,
        "hotel": r.hotel,
        "flight": r.flight,
        "start": r.start.isoformat() if r.start else None,
        "end": r.end.isoformat() if r.end else None,
        "registrationKind": _status_kind(r.registration),
        "hotelKind": _status_kind(r.hotel),
        "flightKind": _status_kind(r.flight),
    }


def _render_html(rows: list[Row], today: date, source_csv: str, title_year: str) -> str:
    def sort_key(r: Row) -> tuple[Any, Any, str, str]:
        # Put TBD dates last.
        start_key = r.start or date.max
        end_key = r.end or date.max
        return (start_key, end_key, r.conference, r.paper)

    rows_sorted = sorted(rows, key=sort_key)
    data = [_row_to_dict(r) for r in rows_sorted]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Presentations {title_year}</title>
  <style>
    :root {{
      --bg: #0b1220;
      --panel: rgba(255,255,255,0.06);
      --panel2: rgba(255,255,255,0.10);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.68);
      --faint: rgba(255,255,255,0.50);
      --border: rgba(255,255,255,0.12);
      --shadow: 0 18px 50px rgba(0,0,0,0.35);
      --accent: #79c0ff;
      --good: #2dd4bf;
      --bad: #fb7185;
      --warn: #fbbf24;
      --na: rgba(255,255,255,0.35);
      --chip: rgba(255,255,255,0.08);
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font-family: var(--sans);
      color: var(--text);
      background:
        radial-gradient(1100px 650px at 20% 10%, rgba(121,192,255,0.25), transparent 60%),
        radial-gradient(900px 600px at 80% 30%, rgba(45,212,191,0.18), transparent 60%),
        radial-gradient(700px 500px at 50% 95%, rgba(251,191,36,0.12), transparent 60%),
        var(--bg);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 28px 18px 48px; }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 14px 18px;
      border: 1px solid var(--border);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    h1 {{ font-size: 22px; margin: 0 0 4px; letter-spacing: 0.2px; }}
    .sub {{ font-size: 13px; color: var(--muted); }}
    .sub code {{ font-family: var(--mono); font-size: 12px; color: var(--text); }}
    .controls {{
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr 1fr;
      min-width: min(520px, 100%);
    }}
    @media (max-width: 880px) {{
      header {{ flex-direction: column; align-items: stretch; }}
      .controls {{ grid-template-columns: 1fr; }}
    }}
    .input {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(0,0,0,0.18);
    }}
    .input label {{ font-size: 12px; color: var(--faint); min-width: 70px; }}
    input[type="search"], select {{
      width: 100%;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--text);
      font-size: 13px;
    }}
    select option {{ color: #111; }}
    .stats {{
      margin-top: 16px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }}
    @media (max-width: 880px) {{
      .stats {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    .card {{
      border: 1px solid var(--border);
      border-radius: 16px;
      background: var(--panel);
      box-shadow: 0 12px 40px rgba(0,0,0,0.22);
      padding: 12px 12px 10px;
    }}
    .statNum {{ font-size: 18px; font-weight: 650; letter-spacing: 0.2px; }}
    .statLbl {{ margin-top: 2px; font-size: 12px; color: var(--muted); }}
    .grid {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: 420px 1fr;
      gap: 14px;
    }}
    @media (max-width: 1020px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      border: 1px solid var(--border);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .panelHead {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .panelTitle {{ font-size: 13px; color: var(--muted); letter-spacing: 0.24px; text-transform: uppercase; }}
    .pill {{
      font-family: var(--mono);
      font-size: 12px;
      padding: 6px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.22);
      color: var(--muted);
      white-space: nowrap;
    }}
    .list {{ padding: 10px; display: grid; gap: 10px; }}
    .item {{
      border: 1px solid var(--border);
      border-radius: 16px;
      background: rgba(0,0,0,0.14);
      padding: 11px 12px;
    }}
    .itemTop {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }}
    .paper {{ font-size: 14px; font-weight: 650; line-height: 1.3; }}
    .conf {{ margin-top: 5px; font-size: 13px; color: var(--muted); line-height: 1.3; }}
    .meta {{
      margin-top: 9px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      font-size: 12px;
      color: var(--muted);
      background: var(--chip);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 5px 8px;
      white-space: nowrap;
    }}
    .chip strong {{ color: var(--text); font-weight: 650; }}
    .status {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      display: inline-block;
      background: var(--na);
      box-shadow: 0 0 0 3px rgba(0,0,0,0.22) inset;
    }}
    .dot.yes {{ background: var(--good); }}
    .dot.no {{ background: var(--bad); }}
    .dot.tbd {{ background: var(--warn); }}
    .dot.na {{ background: var(--na); }}
    .timeline {{ padding: 10px 12px 16px; }}
    .month {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 10px 0 8px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.22px;
    }}
    .month:before {{
      content: "";
      flex: 1;
      height: 1px;
      background: var(--border);
    }}
    .month:after {{
      content: "";
      flex: 9;
      height: 1px;
      background: var(--border);
      opacity: 0.7;
    }}
    .line {{
      display: grid;
      grid-template-columns: 130px 1fr;
      gap: 10px;
      padding: 8px 0;
      border-bottom: 1px dashed rgba(255,255,255,0.10);
    }}
    .d {{ font-family: var(--mono); font-size: 12px; color: var(--text); }}
    .t {{ font-size: 13px; color: var(--muted); }}
    .t strong {{ color: var(--text); }}
    .tag {{
      font-size: 11px;
      padding: 3px 7px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,0.22);
      color: var(--muted);
      margin-left: 6px;
    }}
    .tag.me {{ color: rgba(45,212,191,0.95); border-color: rgba(45,212,191,0.35); }}
    .tag.disc {{ color: rgba(251,113,133,0.95); border-color: rgba(251,113,133,0.35); }}
    .tag.pres {{ color: rgba(121,192,255,0.95); border-color: rgba(121,192,255,0.35); }}
    .footer {{
      margin-top: 14px;
      color: var(--faint);
      font-size: 12px;
    }}
    .footer code {{ font-family: var(--mono); font-size: 12px; color: var(--text); }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Presentations & Discussions ({title_year})</h1>
        <div class="sub">
          Built from <code>{source_csv}</code> • Today: <code>{today.isoformat()}</code>
        </div>
      </div>
      <div class="controls">
        <div class="input">
          <label for="q">Search</label>
          <input id="q" type="search" placeholder="paper, conference, location, presenter…" />
        </div>
        <div class="input">
          <label for="filter">Filter</label>
          <select id="filter">
            <option value="all">All</option>
            <option value="mine">Only my items</option>
            <option value="upcoming">Upcoming only</option>
            <option value="missing">Missing travel/registration (mine)</option>
            <option value="discussions">Discussions</option>
            <option value="presentations">Presentations</option>
          </select>
        </div>
      </div>
    </header>

    <div class="stats" id="stats"></div>

    <div class="grid">
      <section class="panel">
        <div class="panelHead">
          <div class="panelTitle">Checklist View</div>
          <div class="pill" id="countPill">0 need action</div>
        </div>
        <div class="list" id="list"></div>
      </section>

      <section class="panel">
        <div class="panelHead">
          <div class="panelTitle">Timeline</div>
          <div class="pill">Sorted by start date</div>
        </div>
        <div class="timeline" id="timeline"></div>
      </section>
    </div>

    <div class="footer">
      Regenerate: <code>python3 conferences/build_dashboard.py</code>
    </div>
  </div>

  <script>
    const TODAY = "{today.isoformat()}";
    const RAW = {json.dumps(data, ensure_ascii=False)};

    function parseISO(d) {{
      // d: YYYY-MM-DD
      if (!d) return null;
      const [y,m,dd] = d.split("-").map(Number);
      return new Date(Date.UTC(y, m-1, dd, 0, 0, 0));
    }}

    function formatRange(startISO, endISO, raw) {{
      if (!raw && !startISO && !endISO) return "TBD";
      if (raw && raw.includes(" to ")) return raw;
      if (!startISO || !endISO || startISO === endISO) return startISO;
      return `${{startISO}} to ${{endISO}}`;
    }}

    function includesCI(hay, needle) {{
      return (hay || "").toLowerCase().includes((needle || "").toLowerCase());
    }}

    function isMe(presenter) {{
      return (presenter || "").trim().toLowerCase() === "me";
    }}

    function isUpcoming(startISO) {{
      const d = parseISO(startISO);
      if (!d) return true; // Treat TBD as upcoming.
      return d >= parseISO(TODAY);
    }}

    function needsChecklist(item) {{
      if (!isMe(item.presenter)) return false;
      const kinds = [item.registrationKind, item.hotelKind, item.flightKind];
      return kinds.includes("no") || kinds.includes("tbd");
    }}

    function esc(s) {{
      return (s || "").replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}}[c]));
    }}

    function chipStatus(label, kind, text) {{
      return `
        <span class="chip status" title="${{esc(text)}}">
          <span class="dot ${{kind}}"></span>
          ${{esc(label)}}: <strong>${{esc(text)}}</strong>
        </span>`;
    }}

    function tagHTML(item) {{
      const role = (item.role || "").toLowerCase();
      const roleTag = role.includes("disc") ? `<span class="tag disc">Discussion</span>` : `<span class="tag pres">Presentation</span>`;
      const meTag = isMe(item.presenter) ? `<span class="tag me">Me</span>` : "";
      return `${{roleTag}}${{meTag}}`;
    }}

    function renderItem(item) {{
      const dateStr = formatRange(item.start, item.end, item.dateRaw);
      const conf = item.conferenceLink
        ? `<a href="${{esc(item.conferenceLink)}}" target="_blank" rel="noreferrer">${{esc(item.conference)}}</a>`
        : esc(item.conference);
      return `
        <div class="item">
          <div class="itemTop">
            <div>
              <div class="paper">${{esc(item.paper)}}</div>
              <div class="conf">${{conf}} • ${{esc(item.location || "—")}}</div>
            </div>
            <div style="text-align:right">
              <div class="d">${{esc(dateStr)}}</div>
              <div style="margin-top:6px">${{tagHTML(item)}}</div>
            </div>
          </div>
          <div class="meta">
            <span class="chip">Presenter: <strong>${{esc(item.presenter || "—")}}</strong></span>
            ${{chipStatus("Registration", item.registrationKind, item.registration || "—")}}
            ${{chipStatus("Hotel", item.hotelKind, item.hotel || "—")}}
            ${{chipStatus("Flight", item.flightKind, item.flight || "—")}}
          </div>
        </div>`;
    }}

    function monthKey(iso) {{
      if (!iso) return "TBD";
      return iso.slice(0, 7); // YYYY-MM
    }}

    function monthLabel(yyyyMm) {{
      if (yyyyMm === "TBD") return "TBD";
      const [y, m] = yyyyMm.split("-").map(Number);
      const d = new Date(Date.UTC(y, m-1, 1));
      return d.toLocaleString(undefined, {{ month: "long", year: "numeric", timeZone: "UTC" }});
    }}

    function renderTimeline(items) {{
      const groups = new Map();
      for (const it of items) {{
        const key = monthKey(it.start);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(it);
      }}
      const keys = Array.from(groups.keys()).sort((a, b) => {{
        if (a === "TBD" && b !== "TBD") return 1;
        if (a !== "TBD" && b === "TBD") return -1;
        return a.localeCompare(b);
      }});
      let html = "";
      for (const k of keys) {{
        html += `<div class="month">${{esc(monthLabel(k))}}</div>`;
        for (const it of groups.get(k)) {{
          const dateStr = formatRange(it.start, it.end, it.dateRaw);
          const conf = it.conferenceLink
            ? `<a href="${{esc(it.conferenceLink)}}" target="_blank" rel="noreferrer"><strong>${{esc(it.conference)}}</strong></a>`
            : `<strong>${{esc(it.conference)}}</strong>`;
          html += `
            <div class="line">
              <div class="d">${{esc(dateStr)}}</div>
              <div class="t">${{conf}} — ${{esc(it.paper)}} ${{tagHTML(it)}}</div>
            </div>`;
        }}
      }}
      return html || `<div class="sub" style="padding:12px 2px">No items match.</div>`;
    }}

    function renderStats(items) {{
      const total = items.length;
      const upcoming = items.filter(it => isUpcoming(it.start)).length;
      const past = total - upcoming;
      const mine = items.filter(it => isMe(it.presenter)).length;
      const missingMine = items.filter(it => needsChecklist(it)).length;
      return [
        {{ n: total, lbl: "Items" }},
        {{ n: mine, lbl: "My items" }},
        {{ n: upcoming, lbl: "Upcoming" }},
        {{ n: missingMine, lbl: "Need action (mine)" }},
      ].map(s => `
        <div class="card">
          <div class="statNum">${{s.n}}</div>
          <div class="statLbl">${{esc(s.lbl)}}</div>
        </div>`).join("");
    }}

    function applyFilter(items, q, filter) {{
      let out = items;
      if (q) {{
        out = out.filter(it =>
          includesCI(it.paper, q) ||
          includesCI(it.conference, q) ||
          includesCI(it.location, q) ||
          includesCI(it.presenter, q) ||
          includesCI(it.role, q)
        );
      }}
      if (filter === "mine") out = out.filter(it => isMe(it.presenter));
      if (filter === "upcoming") out = out.filter(it => isUpcoming(it.start));
      if (filter === "missing") out = out.filter(it => needsChecklist(it));
      if (filter === "discussions") out = out.filter(it => (it.role || "").toLowerCase().includes("disc"));
      if (filter === "presentations") out = out.filter(it => (it.role || "").toLowerCase().includes("pres"));
      return out;
    }}

    function update() {{
      const q = document.getElementById("q").value.trim();
      const filter = document.getElementById("filter").value;
      const items = applyFilter(RAW, q, filter);
      const checklistItems = items.filter(it => needsChecklist(it));

      document.getElementById("stats").innerHTML = renderStats(RAW);
      document.getElementById("countPill").textContent = `${{checklistItems.length}} need action`;
      document.getElementById("list").innerHTML =
        checklistItems.map(renderItem).join("") ||
        `<div class="sub" style="padding:6px 4px">Nothing to do — everything is set.</div>`;
      document.getElementById("timeline").innerHTML = renderTimeline(items);
    }}

    document.getElementById("q").addEventListener("input", update);
    document.getElementById("filter").addEventListener("change", update);
    update();
  </script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build an HTML dashboard from a presentations CSV.")
    parser.add_argument("--csv", dest="csv_path", default="conferences/presentations_2026.csv")
    parser.add_argument("--out", dest="out_path", default="conferences/presentations_2026.html")
    parser.add_argument("--title-year", dest="title_year", default=None)
    args = parser.parse_args(argv[1:])

    csv_path = (repo_root / args.csv_path).resolve()
    out_path = (repo_root / args.out_path).resolve()

    rows = _read_rows(csv_path)
    try:
        source_rel = str(csv_path.relative_to(repo_root))
    except Exception:  # noqa: BLE001
        source_rel = str(csv_path)
    year = args.title_year
    if not year:
        m = re.search(r"(20\d{2})", csv_path.stem)
        year = m.group(1) if m else str(date.today().year)
    html = _render_html(rows, today=date.today(), source_csv=source_rel, title_year=year)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
