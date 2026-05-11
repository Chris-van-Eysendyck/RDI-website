"""
One-time migration: converts the legacy calls.json into the new calls_ledger.csv master.

Run once, then edit calls_ledger.csv directly going forward.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC  = ROOT / "data" / "calls.json"
DEST = ROOT / "data" / "calls_ledger.csv"

# ── Domain assignment (primary domain per call_id in legacy JSON) ─────────────
DOMAIN_MAP = {
    # 2022 calls
    39: "Geopolitics",      # Russia 2-3 provinces
    34: "Macro",            # Germany Russia energy trap
    35: "Geopolitics",      # Russia can't win
    32: "Politics-EU",      # Truss mini-budget
    33: "Macro",            # Peak inflation
    36: "Politics-EU",      # Belgium govt falls
    37: "Macro",            # Nuclear renaissance
    38: "Macro",            # Rates won't surge
    # 2023 calls
    27: "Geopolitics",      # Gaza/Saudi normalization
    28: "Geopolitics",      # Ukraine stalemate
    29: "Geopolitics",      # Iran nuclear
    31: "Geopolitics",      # 2024 elections most consequential
    30: "Geopolitics",      # China demographic peak
    # 2024 calls
    24: "Politics-EU",      # Belgium election — gets poorer
    25: "Markets",          # Nvidia call
    26: "Markets",          # Healthcare & financials
    19: "Macro",            # France bond spreads
    20: "Geopolitics",      # Trump tariffs
    21: "Politics-EU",      # Germany stagnation
    22: "Geopolitics",      # Ukraine no ceasefire
    23: "Geopolitics",      # No Taiwan invasion
    # 2025 calls
    1:  "Politics-EU",      # France debt/political paralysis
    2:  "Politics-EU",      # EU populist wave
    3:  "Markets",          # US markets outperform on AI
    4:  "Geopolitics",      # Gaza siege continues
    5:  "Geopolitics",      # Taiwan pressure campaign
    6:  "Geopolitics",      # Syria Assad collapse
    7:  "Geopolitics",      # Ukraine ceasefire by end-2025
    18: "Geopolitics",      # EU sidelined from peace talks
    # 2026 calls
    8:  "Macro",            # Oil prices structurally capped
    9:  "Markets",          # Gold stays elevated
    10: "Geopolitics",      # Ukraine frozen conflict
    11: "Geopolitics",      # No Taiwan invasion 2026
    12: "Tech-AI",          # China EUV chip independence
    13: "Politics-EU",      # EU remains institutionally intact
    14: "Geopolitics",      # Japan-China tensions
    15: "Tech-AI",          # US AI bubble not burst
    16: "Macro",            # US labor market deteriorates
    17: "Macro",            # Japan yen currency crisis
}

TAGS_MAP = {
    39: "Ukraine|Russia|war|2022",
    34: "Germany|Russia|energy|gas|geopolitics",
    35: "Russia|Ukraine|war|stalemate",
    32: "UK|Truss|fiscal|bonds|sterling",
    33: "inflation|rates|Fed|ECB|cycle",
    36: "Belgium|politics|coalition",
    37: "nuclear|energy|SMR|Europe",
    38: "rates|Fed|ECB|debt|fiscal",
    27: "Gaza|Saudi Arabia|Israel|Iran|normalization|October7",
    28: "Ukraine|Russia|stalemate|war",
    29: "Iran|nuclear|Middle East|proliferation",
    31: "elections|democracy|2024|geopolitics",
    30: "China|demographics|population|decline",
    24: "Belgium|election|fiscal|deficit",
    25: "Nvidia|AI|semiconductors|markets",
    26: "healthcare|financials|equities|returns",
    19: "France|bonds|OAT|Bund|spread|fiscal",
    20: "Trump|tariffs|trade war|China|EU",
    21: "Germany|stagnation|EU|leadership",
    22: "Ukraine|ceasefire|Russia|peace",
    23: "Taiwan|China|invasion|PLA",
    1:  "France|debt|fiscal|OAT|Bund|spread|politics",
    2:  "EU|populism|right-wing|elections|Germany|France",
    3:  "US|equities|AI|markets|S&P",
    4:  "Gaza|ceasefire|Middle East|Israel",
    5:  "Taiwan|China|coercion|PLA|geopolitics",
    6:  "Syria|Assad|regime|collapse",
    7:  "Ukraine|ceasefire|Russia|peace",
    18: "EU|Ukraine|peace|Riyadh|geopolitics",
    8:  "oil|OPEC|Russia|oversupply|fiscal",
    9:  "gold|central banks|inflation|real rates",
    10: "Ukraine|frozen conflict|Russia|peace",
    11: "Taiwan|China|invasion|PLA",
    12: "China|semiconductors|EUV|ASML|chips",
    13: "EU|institutions|integrity|politics",
    14: "Japan|China|Senkaku|Taiwan|Takaichi",
    15: "AI|bubble|tech|valuations|US",
    16: "US|labor|unemployment|credit|private credit",
    17: "Japan|yen|carry trade|Takaichi|BoJ|FX intervention",
}

TIME_HORIZON_MAP = {
    39: "within 12 months (from Feb 2022)",
    34: "multi-year (2022–2024)",
    35: "within 18 months",
    32: "within weeks",
    33: "by end-2023",
    36: "within 2023",
    37: "3–5 year horizon",
    38: "by end-2023",
    27: "by end-2024",
    28: "through 2024",
    29: "5–10 year horizon",
    31: "by end-2024",
    30: "30–40 year horizon (structural)",
    24: "by end-2024",
    25: "ongoing / multi-year",
    26: "by end-2024",
    19: "through 2025",
    20: "through 2025",
    21: "through 2025",
    22: "by Q3 2025",
    23: "through 2025",
    1:  "through 2025",
    2:  "through 2025",
    3:  "through 2025",
    4:  "through 2025",
    5:  "through 2025",
    6:  "through 2025",
    7:  "by end-2025",
    18: "by mid-2025",
    8:  "through 2026",
    9:  "through 2026",
    10: "through 2026",
    11: "through 2026",
    12: "5–10 year horizon (progress milestone by end-2026)",
    13: "through 2026",
    14: "through 2026",
    15: "through 2026",
    16: "through 2026",
    17: "within 12 months (from Jan 2026)",
}

PRE_CONSENSUS_MAP = {
    # True = this was against prevailing consensus when made
    39: True,   # Written day 1 of invasion — against "Putin will win quickly" consensus
    34: True,   # Energy trap — against "Germany will quickly diversify" narrative
    35: True,   # "Russia can't win" — rare take early in war
    32: True,   # Truss budget will destroy govt — went against initial market reaction
    33: True,   # Peak inflation imminent — consensus was rates had to go much higher
    36: False,  # Belgium govt collapse — widely expected
    37: True,   # Nuclear renaissance — against green-energy consensus
    38: True,   # Rates won't surge much higher — contrarian in Sept 2022
    27: True,   # Gaza derails Saudi-Israel normalization — against "contained" consensus
    28: False,  # Ukraine stalemate — becoming consensus by Nov 2023
    29: False,  # Iran nuclear threshold — widely reported
    31: False,  # 2024 most consequential election year — near-consensus
    30: False,  # China demographic decline — established fact by 2023
    24: True,   # Belgium will get poorer regardless — against political messaging
    25: True,   # Nvidia buy — "laughed out of a meeting"
    26: False,  # Healthcare/financials safe — defensible consensus
    19: True,   # France spreads widen — called early (already at GFC widest)
    20: False,  # Trump tariffs — expected after election win
    21: False,  # Germany stagnation — widely recognised
    22: True,   # Ukraine ceasefire Q2/Q3 2025 — optimistic call, missed
    23: False,  # No Taiwan invasion — consensus
    1:  False,  # France debt crisis — escalation of known trend
    2:  False,  # EU populist wave — confirmed trend
    3:  False,  # US markets outperform — AI theme visible by Jan 2025
    4:  False,  # Gaza siege continues — no ceasefire in sight
    5:  False,  # Taiwan pressure without invasion — consensus
    6:  True,   # Assad regime collapse — called before fall
    7:  True,   # Ukraine ceasefire largely complete by end-2025 — optimistic / contrarian
    18: True,   # EU sidelined from peace — against EU officials' narrative
    8:  True,   # Oil structurally capped — against OPEC+ cut narrative
    9:  False,  # Gold stays elevated — following established trend
    10: False,  # Ukraine frozen conflict — emerging consensus
    11: False,  # No Taiwan invasion — consensus
    12: True,   # China approaching EUV independence — against "never catch up" consensus
    13: False,  # EU intact — consensus
    14: False,  # Japan-China tensions — ongoing trend
    15: False,  # AI bubble doesn't burst — consensus in Jan 2026
    16: True,   # US labor deteriorates materially — against "soft landing" consensus
    17: True,   # Japan yen currency crisis — contrarian at time of writing
}

RESOLUTION_NOTE_MAP = {
    # Only for Resolved calls
    39: "Russia held only 4 south-eastern provinces; negotiations began from exhaustion on both sides — consistent with the call.",
    34: "Germany paid Russia €200M/day through 2022; took years and massive cost to reduce dependency.",
    35: "No decisive Russian victory after 3 years; best outcome was negotiated settlement from exhaustion.",
    32: "Truss resigned 21 days after the mini-budget; sterling fell, BoE intervened.",
    33: "US inflation peaked Jun 2022; Fed terminal rate ~5.25% vs expectations of 6%+; cycle ended May 2023.",
    36: "WRONG: De Croo coalition survived to June 2024 elections, propped up by absence of alternatives.",
    37: "Multiple EU countries reversed nuclear phase-outs (Germany extended life of last plants, France restarted builds, Belgium extended Tihange).",
    38: "Fed paused at 5.25–5.50% (not 6%+); ECB at 4.5%. Neither went substantially beyond late-2022 levels.",
    27: "Saudi-Israel normalization collapsed after October 7; Iran gained influence; Hamas retained control of Gaza.",
    28: "Stalemate held through 2024; Riyadh talks only began in late 2025.",
    30: "China reported population decline every year from 2022; demographic trajectory confirmed locked in.",
    31: "2024: US, EU Parliament, UK, India elections all shifted political landscape dramatically.",
    24: "All major Belgian parties' 2024 programs widened deficit; country in fiscal crisis by 2026.",
    25: "Nvidia became one of the most valuable companies on earth by 2024; call validated spectacularly.",
    26: "Healthcare and financials averaged 9–10% price returns in 2024 with minimal downside volatility.",
    19: "French OAT-Bund spread widened to widest since GFC; France lost AAA at S&P in 2024.",
    20: "Trump's 2025 tariff package exceeded expectations; retaliatory measures from China, EU, Canada.",
    21: "Germany GDP contracted in 2024; no fiscal stimulus; AfD surged; CDU-led coalition inherited stagnation.",
    22: "WRONG: No meaningful ceasefire by Q3 2025; Riyadh talks barely began by year-end.",
    23: "PLA conducted pressure exercises but no invasion; 2025 assessment: still not ready.",
    1:  "France spreads hit 90bp over Germany; constitutional crisis averted but government paralysis continued.",
    2:  "FPÖ won Austrian election; AfD came 2nd in Germany; populists gained in Poland, Netherlands.",
    3:  "S&P 500 up ~25% in 2025; European indices underperformed materially.",
    4:  "Gaza siege continued; 90%+ displacement; no durable ceasefire despite multiple short pauses.",
    5:  "China conducted major exercises; ADIZ incursions; no kinetic action.",
    6:  "Assad regime fell December 8, 2024; called before the HTS offensive completed.",
    7:  "WRONG: No ceasefire by end-2025; talks began in Riyadh but no formal settlement.",
    18: "EU excluded from Riyadh talks; US-Russia bilateral format confirmed; EU side-lined.",
    # 2026 calls — all Open/Pending at time of writing
}

def conviction_from_weight(call):
    year = call.get("year", 0)
    w = call.get("weight")
    if year < 2025 or w is None:
        return ""
    if w == 2: return "★★"
    if w == 1: return "★"
    if w == 0: return "—"
    return ""

def status_from_outcome(outcome):
    if outcome == "success": return "Resolved-Hit"
    if outcome == "failed":  return "Resolved-Miss"
    return "Open"

def sort_key(call):
    from datetime import date
    try:
        d = date.fromisoformat(call["date"])
    except:
        d = date(call.get("year", 2020), 1, 1)
    return (call.get("year", 0), d)

def build_call_id_map(calls):
    by_year = {}
    for c in calls:
        y = c.get("year", 0)
        by_year.setdefault(y, []).append(c)
    for y in by_year:
        by_year[y].sort(key=sort_key)
    id_map = {}
    for y, group in by_year.items():
        for i, c in enumerate(group, start=1):
            id_map[c["id"]] = f"{y}-{i:03d}"
    return id_map

def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    calls = data["calls"]

    id_map = build_call_id_map(calls)

    fieldnames = [
        "call_id", "date_made", "call_text", "domain", "tags",
        "conviction", "time_horizon", "status", "resolution_date",
        "resolution_note", "source_url", "source_title",
        "related_calls", "pre_consensus_score", "confidence_band",
    ]

    # Sort rows for CSV: by year then by date
    calls_sorted = sorted(calls, key=sort_key)

    with open(DEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for c in calls_sorted:
            old_id = c["id"]
            call_id = id_map[old_id]
            outcome = c.get("outcome", "pending")
            status = status_from_outcome(outcome)
            res_note = RESOLUTION_NOTE_MAP.get(old_id, "")
            # Only set resolution_date for resolved calls — leave blank so Christophe can fill in exact dates
            res_date = ""

            writer.writerow({
                "call_id": call_id,
                "date_made": c.get("date", ""),
                "call_text": c.get("description", ""),
                "domain": DOMAIN_MAP.get(old_id, "Geopolitics"),
                "tags": TAGS_MAP.get(old_id, ""),
                "conviction": conviction_from_weight(c),
                "time_horizon": TIME_HORIZON_MAP.get(old_id, ""),
                "status": status,
                "resolution_date": res_date,
                "resolution_note": res_note,
                "source_url": c.get("article_url", ""),
                "source_title": c.get("article_title", ""),
                "related_calls": "",
                "pre_consensus_score": "TRUE" if PRE_CONSENSUS_MAP.get(old_id, False) else "FALSE",
                "confidence_band": "",
            })

    print(f"Written {len(calls)} calls -> {DEST}")
    print("\nCall ID mapping (old id -> new call_id):")
    for old_id, new_id in sorted(id_map.items(), key=lambda x: x[1]):
        print(f"  {old_id:>3} -> {new_id}")

if __name__ == "__main__":
    main()
