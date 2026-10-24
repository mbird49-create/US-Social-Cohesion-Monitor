"""Weekly release check for the slow sources. HTOPS does its own discovery in htops.py.

Writes data/processed/freshness.json: for each source, when it was checked, the newest release on disk,
and whether a newer release appears to exist upstream (which needs a person to review before it is added,
because question wording and coding must be checked first).
"""
import json
import urllib.request
from datetime import date, datetime

from common import OUT, RAW

UA = {"User-Agent": "Mozilla/5.0 (social-cohesion pipeline)"}
GSS_ZIP = "https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_stata.zip"
CPS = "https://www2.census.gov/programs-surveys/cps/datasets/{y}/supp/sep{yy}pub.csv"
OI_META = "https://data.humdata.org/api/3/action/package_show?id=social-capital-atlas"
CPS_LATEST_USED = 2023
OI_LAST_MODIFIED_USED = "2022-08-01"


def head(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001 - network failure is recorded, not fatal
        return None, None


def main():
    today = date.today().isoformat()
    out = {"checked": today, "sources": {}}

    status, modified = head(GSS_ZIP)
    local = datetime.fromtimestamp((RAW / "gss" / "GSS_stata.zip").stat().st_mtime).date().isoformat()
    remote = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat() if modified else None
    out["sources"]["gss"] = {
        "label": "General Social Survey", "release_used": "1972-2024 cumulative, R3a", "downloaded": local,
        "remote_last_modified": remote, "reachable": status == 200,
        "update_available": bool(remote and remote > local),
        "cadence": "Every two years; release about 6-12 months after fieldwork",
    }

    nxt = CPS_LATEST_USED + 2
    status, _ = head(CPS.format(y=nxt, yy=str(nxt)[2:]))
    out["sources"]["cps"] = {
        "label": "CPS Civic Engagement and Volunteering Supplement", "release_used": f"September {CPS_LATEST_USED}",
        "next_expected": f"September {nxt}", "reachable": status is not None,
        "update_available": status == 200,
        "cadence": "Every two years (September); microdata about a year later",
    }

    try:
        with urllib.request.urlopen(urllib.request.Request(OI_META, headers=UA), timeout=30) as r:
            res = json.load(r)["result"]["resources"]
        county = next(x for x in res if "Counties" in x["name"])
        oi_mod = (county.get("last_modified") or "")[:10]
        oi_reach = True
    except Exception:  # noqa: BLE001
        oi_mod, oi_reach = None, False
    out["sources"]["oi"] = {
        "label": "Opportunity Insights Social Capital Atlas", "release_used": "2022 (data from 2018-2019)",
        "remote_last_modified": oi_mod, "reachable": oi_reach,
        "update_available": bool(oi_mod and oi_mod > OI_LAST_MODIFIED_USED),
        "cadence": "One-off release; no update schedule announced",
    }

    waves = json.loads((RAW / "htops" / "waves.json").read_text())
    latest = max(waves)
    out["sources"]["htops"] = {
        "label": "Household Trends and Outlook Pulse Survey", "release_used": f"Wave {latest}",
        "collected": f"{waves[latest]['start']} to {waves[latest]['end']}", "reachable": True,
        "update_available": False,  # new waves are downloaded automatically by htops.py
        "cadence": "About every two months; tables a few weeks after collection",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "freshness.json").write_text(json.dumps(out, indent=1))
    flagged = [k for k, v in out["sources"].items() if v["update_available"]]
    print(f"freshness: checked {today}; newer upstream release for: {', '.join(flagged) or 'none'}")


if __name__ == "__main__":
    main()
