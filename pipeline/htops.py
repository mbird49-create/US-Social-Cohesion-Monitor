"""Census Household Trends and Outlook Pulse Survey (HTOPS) published tables -> national well-being and close-tie estimates.

This is the freshest source in the app: a wave about every two months. Each run looks up the Census table index,
downloads any wave not yet on disk, and parses the national ("US") sheet of each table.
Tables are matched by question header text, not file name, because numbering changes between waves.

Estimate: share of adults 18+ in the positive categories among those who answered ("Did not report" removed).
SE: from Census's published SE tables. Where several categories are summed, their covariance is ignored (approximate).
"""
import json
import re
import urllib.request
from datetime import datetime

import numpy as np
import pandas as pd

from common import OUT, RAW

BASE = "https://www2.census.gov/programs-surveys/demo/tables/hhp"
PAGE = "https://www.census.gov/data/tables/{year}/demo/hhp/{wave}.html"
DIR = RAW / "htops"
FIRST_YEAR = 2026  # March 2026 began the cross-sectional design; earlier waves are not comparable.

# metric id: (question header substring, positive category labels)
ITEMS = {
    "htops_lonely": ("loneliness", {"Always", "Usually", "Always or Usually"}),
    "htops_support": ("social and emotional support", {"Always", "Usually", "Always or Usually"}),
    "htops_inperson": ("Gets together in person", {"1 or 2 times a week", "3 or 4 times a week", "5 or more times a week"}),
    "htops_clubs": ("meetings of clubs or organizations", {"1 to 3 times", "4 to 11 times", "12 or more times"}),
    "htops_anxiety": ("nervous, anxious, or on edge", {"More than half the days", "Nearly every day"}),
    "htops_depression": ("down, depressed, or hopeless", {"More than half the days", "Nearly every day"}),
    "htops_food_insufficient": ("Food sufficiency", {"Sometimes not enough to eat", "Often not enough to eat",
                                                     "Sometimes or often not enough to eat"}),
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (social-cohesion pipeline)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def discover_and_download():
    """Download health/food tables for every wave from FIRST_YEAR onward. Returns {wave: collection period}."""
    meta_path = DIR / "waves.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for year in range(FIRST_YEAR, datetime.now().year + 1):
        try:
            index = fetch(f"{BASE}/{year}/").decode()
        except Exception as e:  # noqa: BLE001 - a missing year folder is normal
            print(f"htops: no index for {year} ({e})")
            continue
        for wave in sorted(set(re.findall(r'href="(\d{4})/"', index))):
            wdir = DIR / wave
            files = re.findall(r'href="((?:health|food)[a-z0-9_]*\.xlsx)"', fetch(f"{BASE}/{year}/{wave}/").decode())
            if not files:
                continue  # wave folder exists but these topics were not published
            wdir.mkdir(parents=True, exist_ok=True)
            for f in files:
                if not (wdir / f).exists():
                    (wdir / f).write_bytes(fetch(f"{BASE}/{year}/{wave}/{f}"))
            if wave not in meta:
                html = fetch(PAGE.format(year=year, wave=wave)).decode(errors="ignore")
                m = re.search(r"collected[^.]{0,80}?during\s+([A-Z][a-z]+ \d{1,2})\s*[–-]\s*([A-Z][a-z]+ \d{1,2}),?\s*(\d{4})", html)
                if not m:
                    m = re.search(r"during\s+([A-Z][a-z]+ \d{1,2})\s*[–-]\s*([A-Z][a-z]+ \d{1,2}),?\s*(\d{4})", html)
                if m:
                    start = datetime.strptime(f"{m[1]} {m[3]}", "%B %d %Y").date().isoformat()
                    end = datetime.strptime(f"{m[2]} {m[3]}", "%B %d %Y").date().isoformat()
                    meta[wave] = {"start": start, "end": end, "page": PAGE.format(year=year, wave=wave)}
                else:
                    meta[wave] = {"start": None, "end": None, "page": PAGE.format(year=year, wave=wave)}
    meta_path.write_text(json.dumps(meta, indent=1))
    return meta


def read_table(path):
    """National sheet -> (question per column, category per column, Total-row values)."""
    d = pd.read_excel(path, sheet_name=0, header=None)
    q_row = d.index[d.iloc[:, 0].astype(str).str.strip() == "Select characteristics"][0]
    total_row = d.index[(d.index > q_row) & (d.iloc[:, 0].astype(str).str.strip() == "Total")][0]
    questions = d.iloc[q_row].ffill().astype(str).tolist()
    cats = d.iloc[q_row + 1].astype(str).str.strip().tolist()
    vals = pd.to_numeric(d.iloc[total_row], errors="coerce").tolist()
    universe = str(d.iloc[q_row - 1, 0]).strip()
    return questions, cats, vals, universe


def estimate(wdir, needle, positive):
    for path in sorted(wdir.glob("*.xlsx")):
        if path.stem.endswith("_se"):
            continue
        qs, cats, vals, universe = read_table(path)
        cols = [i for i, q in enumerate(qs) if needle.lower() in q.lower() and i > 1]
        if not cols:
            continue
        pos = [i for i in cols if cats[i] in positive]
        missing = [i for i in cols if cats[i] == "Did not report"]
        if not pos:
            raise ValueError(f"{path}: '{needle}' found but no positive categories among {[cats[i] for i in cols]}")
        answered = sum(vals[i] for i in cols) - sum(vals[i] for i in missing)
        value = sum(vals[i] for i in pos) / answered
        se_path = path.with_name(path.stem + "_se.xlsx")
        se = None
        if se_path.exists():
            _, _, se_vals, _ = read_table(se_path)
            se = float(np.sqrt(sum(se_vals[i] ** 2 for i in pos)) / answered)
        return {"value": float(value), "se": se, "question": qs[cols[0]], "categories": [cats[i] for i in pos],
                "universe": universe, "item_nonresponse": float(sum(vals[i] for i in missing) / sum(vals[i] for i in cols)),
                "table": path.name}
    return None


def main():
    meta = discover_and_download()
    rows = []
    for wave, info in sorted(meta.items()):
        wdir = DIR / wave
        for metric, (needle, positive) in ITEMS.items():
            r = estimate(wdir, needle, positive)
            if r:
                rows.append({"metric": metric, "series": "main", "wave": wave, "year": int("20" + wave[:2]),
                             "period_start": info["start"], "period_end": info["end"], "page": info["page"], **r})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "htops_national.json").write_text(json.dumps(rows, indent=1))
    print(f"htops: {len(rows)} estimates from waves {', '.join(sorted(meta))}")


if __name__ == "__main__":
    main()
