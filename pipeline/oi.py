"""Opportunity Insights Social Capital Atlas (2022 release, county file) -> state network measures.

  - economic connectedness (bridging): defined for below-median-SES people, so counties are weighted by num_below_p50.
  - clustering and support ratio (bonding / network density): defined for all users, so counties are weighted by pop2018.
State figures are derived here; OI does not publish them. SEs (EC only) treat county errors as independent (approximate).
"""
import json

import numpy as np
import pandas as pd

from common import OUT, RAW, STATES

CSV = RAW / "oi" / "social_capital_county.csv"

# metric id: (value column, SE column or None, county weight column)
ITEMS = {
    "oi_economic_connectedness": ("ec_county", "ec_se_county", "num_below_p50"),
    "oi_clustering": ("clustering_county", None, "pop2018"),
    "oi_support_ratio": ("support_ratio_county", None, "pop2018"),
}


def main():
    df = pd.read_csv(CSV)
    df["fips"] = df.county // 1000
    total_pop = df.groupby("fips").pop2018.sum()
    rows, national = [], []
    for metric, (col, se_col, wcol) in ITEMS.items():
        v = df.dropna(subset=[col, wcol])
        for fips, g in v.groupby("fips"):
            w = g[wcol].to_numpy(float)
            se = None
            if se_col:
                s = g[se_col].fillna(0).to_numpy(float)
                se = float(np.sqrt(np.sum((w / w.sum()) ** 2 * s ** 2)))
            abbr, name = STATES[int(fips)]
            rows.append({"metric": metric, "year": 2022, "fips": int(fips), "abbr": abbr, "state": name,
                         "value": float(np.sum(w * g[col]) / w.sum()), "se": se, "n_counties": int(len(g)),
                         "pop_coverage": float(g.pop2018.sum() / total_pop[fips])})
        w = v[wcol].to_numpy(float)
        national.append({"metric": metric, "year": 2022, "variable": col, "value": float(np.sum(w * v[col]) / w.sum()),
                         "se": None, "pop_coverage": float(v.pop2018.sum() / df.pop2018.sum())})
        print(f"oi {metric}: national {national[-1]['value']:.3f}, coverage {national[-1]['pop_coverage']:.3f}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "oi_state.json").write_text(json.dumps(rows, indent=1))
    (OUT / "oi_national.json").write_text(json.dumps(national, indent=1))


if __name__ == "__main__":
    main()
