"""
Prerenders the calls ledger into static HTML so the track record is visible
to crawlers, AI assistants, and no-JS clients — not just to browsers running JS.

What it does
------------
  1. Regenerates data/ledger.json from data/calls_ledger.csv (via export_json.py)
  2. calls.html:
       - embeds the full ledger as inline JSON (read by the page JS — no fetch)
       - prerenders the score cards (#score-grid) and call cards (#calls-list)
         using the exact same markup and scoring logic as the page JS
       - injects a JSON-LD Dataset block for SEO
  3. index.html:
       - bakes headline stats (total calls, weighted success rate, regions)
         computed from the canonical ledger

Idempotent: content is replaced between PRERENDER marker comments, so it can
be re-run every time calls_ledger.csv changes. Run before committing:

    py scripts/prerender.py

Scoring rules (must match calls.html JS `computeScore`)
-------------------------------------------------------
  2025+   : weighted — ★★=2, ★=1, passive=0 (excluded)
  pre-2025: simple 1/0 accuracy
  'all'   : weighted 2025+ calls and pre-2025 simple calls pooled together
  Hits = Resolved-Hit. Misses = Resolved-Miss, Resolved-Partial.
  Voided excluded from scoring but counts as resolved (not "open").
"""
import json
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

HIT = {"Resolved-Hit"}
MISS = {"Resolved-Miss", "Resolved-Partial"}
RESOLVED = HIT | MISS | {"Voided"}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ── helpers ──────────────────────────────────────────────────────────

def esc(s):
    return html.escape(str(s or ""), quote=True)


def format_date(d):
    """Match JS toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'})."""
    try:
        y, m, dd = (int(x) for x in str(d).split("-")[:3])
        return f"{dd} {MONTHS[m - 1]} {y}"
    except Exception:
        return esc(d)


def call_headline(c):
    text = c.get("call_text") or ""
    m = re.search(r"[.!?\u2014]", text)
    stop = m.start() if m else -1
    if 0 < stop < 110:
        return text[: stop + 1]
    return text[:100] + ("\u2026" if len(text) > 100 else "")


def is_hit(c):
    return c["status"] in HIT


def is_resolved(c):
    return c["status"] in RESOLVED


# ── scoring (mirror of JS computeScore) ──────────────────────────────

def compute_score(calls, year):
    subset = [c for c in calls if year == "all" or c["year"] == year]
    resolved = [c for c in subset if is_resolved(c)]

    if year == "all" or (isinstance(year, int) and year >= 2025):
        weighted = [c for c in resolved if c["year"] >= 2025 and (c.get("weight") or 0) > 0]
        simple = [c for c in resolved if c["year"] < 2025]
        max_w = sum(c["weight"] for c in weighted) + len(simple)
        got_w = sum(c["weight"] for c in weighted if is_hit(c)) + sum(1 for c in simple if is_hit(c))
    else:
        max_w = len(resolved)
        got_w = sum(1 for c in resolved if is_hit(c))

    return {"maxW": max_w, "gotW": got_w, "resolved": len(resolved), "total": len(subset)}


def score_display(sc):
    if sc["resolved"] == 0 or sc["maxW"] == 0:
        return {"label": "\u2014", "pct": 0}
    pct = round(sc["gotW"] / sc["maxW"] * 100)
    return {"label": f'{sc["gotW"]}/{sc["maxW"]}', "pct": pct}


# ── HTML generation (mirror of JS renderScoreCards / renderCalls) ────

def render_score_cards(calls):
    years = sorted({c["year"] for c in calls if c["year"]}, reverse=True)
    out = []
    for yr in years:
        sc = compute_score(calls, yr)
        dis = score_display(sc)
        pending = sc["total"] - sc["resolved"]
        label = (f'{dis["pct"]}% accuracy' if dis["pct"] > 0 else "No resolved calls yet")
        if pending > 0:
            label += f" \u00b7 {pending} open"
        out.append(f'''          <div class="score-card" data-year="{yr}" style="cursor:pointer" title="Filter by {yr}">
            <div class="score-card-year">{yr}{' \u00b7 Weighted' if yr >= 2025 else ''}</div>
            <div class="score-card-value">{dis["label"]}</div>
            <div class="score-card-label">{label}</div>
            <div class="score-bar"><div class="score-bar-fill" data-width="{dis["pct"]}" style="width:{dis["pct"]}%"></div></div>
          </div>''')
    return "\n".join(out)


def weight_label(c):
    if c["year"] < 2025:
        return '<span class="weight-label" style="color:var(--text-dim)">Unweighted</span>'
    w = c.get("weight")
    if w == 2:
        return '<span class="weight-stars">\u2605\u2605</span><span class="weight-label">Important</span>'
    if w == 1:
        return '<span class="weight-stars">\u2605</span><span class="weight-label">Normal</span>'
    if w == 0:
        return '<span class="weight-stars" style="color:var(--text-dim)">\u2014</span><span class="weight-label">Passive</span>'
    return ""


def status_label(c):
    s = c["status"]
    if s == "Resolved-Hit":
        return '<span class="outcome-badge success">\u2713 Correct</span>'
    if s == "Resolved-Miss":
        return '<span class="outcome-badge failed">\u2717 Missed</span>'
    if s == "Resolved-Partial":
        return '<span class="outcome-badge partial">~ Partial</span>'
    if s == "Voided":
        return '<span class="outcome-badge" style="color:var(--text-dim)">\u2014 Voided</span>'
    return '<span class="outcome-badge pending">\u23f3 Open</span>'


def tags_html(tags):
    if not tags:
        return ""
    inner = "".join(f'<span class="call-tag">{esc(t)}</span>' for t in tags[:5])
    return f'<div class="call-tags">{inner}</div>'


def render_calls(calls):
    subset = sorted(calls, key=lambda c: (-(c["year"] or 0), str(c.get("date_made") or "")), reverse=False)
    subset = sorted(calls, key=lambda c: ((c["year"] or 0), str(c.get("date_made") or "")), reverse=True)
    out = []
    for c in subset:
        status_class = ("success" if c["status"] in HIT
                        else "failed" if c["status"] in MISS
                        else "pending")
        horizon = (f'<div class="call-horizon">\u23f1 {esc(c["time_horizon"])}</div>'
                   if c.get("time_horizon") else "")
        resolution = (f'<div class="call-resolution">Resolution: {esc(c["resolution_note"])}</div>'
                      if c.get("resolution_note") else "")
        link = (f'<a class="call-link" href="{esc(c["source_url"])}" target="_blank" rel="noopener">\u2197 {esc(c.get("source_title") or "Source")}</a>'
                if c.get("source_url") else "")
        out.append(f'''          <div class="call-card {status_class}-card">
            <div class="call-left">
              <div class="call-meta">
                <span class="call-date">{format_date(c["date_made"])}</span>
                <span class="call-region">{esc(c["domain"])}</span>
                <span class="call-id-badge">{esc(c["call_id"])}</span>
              </div>
              <div class="call-title">{esc(call_headline(c))}</div>
              <div class="call-desc">{esc(c["call_text"])}</div>
              {horizon}
              {resolution}
              {tags_html(c.get("tags"))}
              {link}
            </div>
            <div class="call-right">
              {status_label(c)}
              <div class="weight-badge">{weight_label(c)}</div>
            </div>
          </div>''')
    return "\n".join(out)


def render_jsonld(calls, sc_all):
    dis = score_display(sc_all)
    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Raven Data Insights \u2014 Public Call Ledger",
        "description": (
            f"Geopolitical and macro forecasts documented before the fact and publicly scored on resolution. "
            f"{len(calls)} calls tracked since 2022; conviction-weighted accuracy {dis['pct']}% "
            f"across resolved calls. Hits and misses both published."
        ),
        "url": "https://realistdata.com/calls",
        "creator": {"@type": "Organization", "name": "Raven Data Insights", "url": "https://realistdata.com"},
        "dateModified": date.today().isoformat(),
        "license": "https://realistdata.com",
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Total calls", "value": len(calls)},
            {"@type": "PropertyValue", "name": "Weighted accuracy (resolved)", "value": f"{dis['pct']}%"},
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ── marker replacement ───────────────────────────────────────────────

def replace_between(text, start, end, new_content, path):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"ERROR: markers {start!r} not found in {path}")
    return pattern.sub(start + "\n" + new_content + "\n" + end, text, count=1)


def safe_json_embed(obj):
    """JSON for inline <script> embedding: escape </ to avoid closing the tag."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


# ── main ─────────────────────────────────────────────────────────────

def main():
    # 1. Regenerate ledger.json from the canonical CSV
    import export_json
    export_json.main()

    ledger = json.loads((ROOT / "data" / "ledger.json").read_text(encoding="utf-8"))
    calls = ledger["calls"]

    # 2. calls.html
    calls_path = ROOT / "calls.html"
    doc = calls_path.read_text(encoding="utf-8")

    doc = replace_between(doc, "<!--PRERENDER:LEDGER-DATA:START-->", "<!--PRERENDER:LEDGER-DATA:END-->",
                          f'  <script type="application/json" id="ledger-data">{safe_json_embed({"calls": calls})}</script>',
                          calls_path)
    doc = replace_between(doc, "<!--PRERENDER:SCORE-GRID-->", "<!--/PRERENDER-->",
                          render_score_cards(calls), calls_path)
    doc = replace_between(doc, "<!--PRERENDER:CALLS-LIST-->", "<!--/PRERENDER-->",
                          render_calls(calls), calls_path)
    doc = replace_between(doc, "<!--PRERENDER:JSONLD:START-->", "<!--PRERENDER:JSONLD:END-->",
                          f'  <script type="application/ld+json">\n{render_jsonld(calls, compute_score(calls, "all"))}\n  </script>',
                          calls_path)
    calls_path.write_text(doc, encoding="utf-8")

    # 3. index.html headline stats (from the canonical ledger, not calls.json)
    idx_path = ROOT / "index.html"
    idx = idx_path.read_text(encoding="utf-8")

    sc_all = compute_score(calls, "all")
    dis = score_display(sc_all)

    # regions still come from calls.json (the map file carries the region field)
    try:
        cj = json.loads((ROOT / "data" / "calls.json").read_text(encoding="utf-8"))
        regions = len({c.get("region") for c in cj["calls"] if not c.get("_placeholder") and c.get("region")})
    except Exception:
        regions = "\u2014"

    idx = replace_between(idx, "<!--PRERENDER:STAT-TOTAL-->", "<!--/PRERENDER-->", str(len(calls)), idx_path)
    idx = replace_between(idx, "<!--PRERENDER:STAT-RATE-->", "<!--/PRERENDER-->", f"{dis['pct']}%", idx_path)
    idx = replace_between(idx, "<!--PRERENDER:STAT-REGIONS-->", "<!--/PRERENDER-->", str(regions), idx_path)
    idx_path.write_text(idx, encoding="utf-8")

    # 4. Report
    open_calls = sum(1 for c in calls if not is_resolved(c))
    print(f"Prerendered {len(calls)} calls into calls.html "
          f"({open_calls} open) \u00b7 headline accuracy {dis['pct']}% ({dis['label']}) "
          f"\u00b7 index stats baked \u00b7 JSON-LD updated")


if __name__ == "__main__":
    main()
