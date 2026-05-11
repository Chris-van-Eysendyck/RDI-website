"""
Computes weighted accuracy from data/ledger.json (or calls_ledger.csv).

Scoring rules
-------------
  2025+  : weighted (weight 2 = important, 1 = normal, 0 = excluded from denominator)
            accuracy = sum(weight * hit) / sum(weight) over resolved non-passive calls
  pre-2025: simple 1/0 accuracy over resolved calls

Usage:
  py scripts/score.py                   # full report
  py scripts/score.py --year 2025       # filter by year
  py scripts/score.py --domain Macro    # filter by domain
  py scripts/score.py --tag yen         # filter by tag
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
SRC  = ROOT / "data" / "ledger.json"

HIT_STATUSES    = {"Resolved-Hit"}
MISS_STATUSES   = {"Resolved-Miss", "Resolved-Partial"}
RESOLVED_ALL    = HIT_STATUSES | MISS_STATUSES | {"Voided"}
SCORED_STATUSES = HIT_STATUSES | MISS_STATUSES   # Voided excluded from score

def is_hit(call):
    return call["status"] in HIT_STATUSES

def is_resolved_scored(call):
    return call["status"] in SCORED_STATUSES

def score_calls(calls):
    """
    Returns dict with weighted and simple accuracy figures.
    """
    weighted_2025 = [c for c in calls if c["year"] and c["year"] >= 2025 and is_resolved_scored(c) and c["weight"] is not None and c["weight"] > 0]
    simple_pre2025 = [c for c in calls if c["year"] and c["year"] < 2025 and is_resolved_scored(c)]

    result = {}

    # Weighted (2025+)
    w_total = sum(c["weight"] for c in weighted_2025)
    w_hit   = sum(c["weight"] for c in weighted_2025 if is_hit(c))
    result["weighted"] = {
        "hits":   w_hit,
        "total":  w_total,
        "pct":    round(w_hit / w_total * 100, 1) if w_total else None,
        "calls":  len(weighted_2025),
    }

    # Simple (pre-2025)
    s_total = len(simple_pre2025)
    s_hit   = sum(1 for c in simple_pre2025 if is_hit(c))
    result["simple"] = {
        "hits":  s_hit,
        "total": s_total,
        "pct":   round(s_hit / s_total * 100, 1) if s_total else None,
        "calls": s_total,
    }

    # Combined headline (weight=1 for pre-2025, actual weight for 2025+)
    all_scored = weighted_2025 + simple_pre2025
    ch_total = w_total + s_total
    ch_hit   = w_hit + s_hit
    result["combined"] = {
        "hits":  ch_hit,
        "total": ch_total,
        "pct":   round(ch_hit / ch_total * 100, 1) if ch_total else None,
        "calls": len(all_scored),
    }

    return result

def print_score(label, sc, indent=0):
    pad = " " * indent
    w = sc.get("weighted", {})
    s = sc.get("simple", {})
    c = sc.get("combined", {})

    lines = []
    if w["total"]:
        lines.append(f"2025+ weighted : {w['hits']}/{w['total']}  ({w['pct']}%,  {w['calls']} calls)")
    if s["total"]:
        lines.append(f"pre-2025 simple: {s['hits']}/{s['total']}  ({s['pct']}%,  {s['calls']} calls)")
    if c["total"]:
        lines.append(f"combined       : {c['hits']}/{c['total']}  ({c['pct']}%,  {c['calls']} resolved scored calls)")

    print(f"\n{pad}{label}")
    print(f"{pad}" + "-" * max(len(label), 40))
    for l in lines:
        print(f"{pad}  {l}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year",   type=int,  help="Filter by year")
    parser.add_argument("--domain", type=str,  help="Filter by domain")
    parser.add_argument("--tag",    type=str,  help="Filter by tag (substring match)")
    args = parser.parse_args()

    data  = json.loads(SRC.read_text(encoding="utf-8"))
    calls = data["calls"]

    # ── Apply filters ─────────────────────────────────────────────────────────
    if args.year:
        calls = [c for c in calls if c["year"] == args.year]
    if args.domain:
        calls = [c for c in calls if c["domain"].lower() == args.domain.lower()]
    if args.tag:
        calls = [c for c in calls if any(args.tag.lower() in t.lower() for t in c["tags"])]

    filter_desc = " | ".join(filter(None, [
        f"year={args.year}" if args.year else None,
        f"domain={args.domain}" if args.domain else None,
        f"tag={args.tag}" if args.tag else None,
    ])) or "all calls"

    print(f"\n=== RDI Scoring Report  [{filter_desc}] ===")
    print(f"Total calls in scope: {len(calls)}")

    resolved = [c for c in calls if is_resolved_scored(c)]
    open_    = [c for c in calls if c["status"] == "Open"]
    voided   = [c for c in calls if c["status"] == "Voided"]
    print(f"  Resolved (scored): {len(resolved)}")
    print(f"  Open:              {len(open_)}")
    print(f"  Voided:            {len(voided)}")

    print_score("OVERALL", score_calls(calls))

    # ── By year ───────────────────────────────────────────────────────────────
    if not args.year:
        years = sorted({c["year"] for c in calls if c["year"]}, reverse=True)
        print("\n\n--- By Year ---")
        for yr in years:
            subset = [c for c in calls if c["year"] == yr]
            print_score(str(yr), score_calls(subset), indent=2)

    # ── By domain ─────────────────────────────────────────────────────────────
    if not args.domain:
        domains = sorted({c["domain"] for c in calls})
        print("\n\n--- By Domain ---")
        for d in domains:
            subset = [c for c in calls if c["domain"] == d]
            print_score(d, score_calls(subset), indent=2)

    # ── Pre-consensus vs consensus ────────────────────────────────────────────
    if not args.tag and not args.domain and not args.year:
        pre  = [c for c in calls if c.get("pre_consensus")]
        post = [c for c in calls if not c.get("pre_consensus")]
        print("\n\n--- By Consensus Position ---")
        print_score("Against consensus at time of call", score_calls(pre),  indent=2)
        print_score("With consensus at time of call",    score_calls(post), indent=2)

    print()

if __name__ == "__main__":
    main()
