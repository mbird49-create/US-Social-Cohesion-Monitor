"""GSS 1972-2024 cumulative file -> national generalized-trust series.

Two series are kept apart, never spliced:
  - "interviewer": TRUST / FAIR / HELPFUL, in-person or phone interviews, 1972-2018, 2022, 2024.
  - "web_nv": TRUSTNV / FAIRNV / HELPFULNV, web self-completion with no volunteered "depends" option, 2021-2024.
The 2021 GSS was web-only and changed how "depends" could be given, so its numbers are not comparable to the interviewer series.
"""
import json

import numpy as np
import pandas as pd

from common import OUT, RAW, kish_se, linearized_se

DTA = RAW / "gss" / "GSS_stata" / "gss7224_r3a.dta"

ITEMS = {
    # metric id: (interviewer variable, web variable, code counted as "positive")
    "gss_trust": ("trust", "trustnv", 1),      # 1 = most people can be trusted
    "gss_fair": ("fair", "fairnv", 2),         # 2 = would try to be fair
    "gss_helpful": ("helpful", "helpfulnv", 1),  # 1 = try to be helpful
    # HAPPY has no web variant variable, so the two series are split by interview mode instead.
    "gss_very_happy": ("happy", None, 1),      # 1 = very happy
}


def estimate(df, var, positive):
    rows = []
    for year, g in df.groupby("year"):
        g = g[g[var].isin([1, 2, 3]) & g.wtssps.notna() & (g.wtssps > 0)]
        if len(g) < 100:
            continue
        y = (g[var] == positive).to_numpy(float)
        w = g.wtssps.to_numpy(float)
        has_design = g.vstrat.notna().all() and g.vpsu.notna().all()
        if has_design:
            se = linearized_se(y, w, g.vstrat.to_numpy(), g.vpsu.to_numpy())
            se_method = "linearized"
        else:
            se, se_method = kish_se(y, w), "kish"
        rows.append({"year": int(year), "value": float(np.sum(w * y) / np.sum(w)), "se": se,
                     "se_method": se_method, "n": int(len(g))})
    return rows


def main():
    cols = ["year", "wtssps", "vstrat", "vpsu", "mode"] + [v for t in ITEMS.values() for v in t[:2] if v]
    df = pd.read_stata(DTA, columns=cols, convert_categoricals=False)
    interviewer = df[df["mode"].isna() | df["mode"].isin([1, 2])]  # in-person or phone; mode is missing before 2021
    web = df[df["mode"] == 4]
    out = []
    for metric, (iv, wv, pos) in ITEMS.items():
        if wv:
            parts = (("interviewer", df, iv), ("web_nv", df, wv))
        else:
            parts = (("interviewer", interviewer, iv), ("web", web, iv))
        for series, frame, var in parts:
            for r in estimate(frame, var, pos):
                out.append({"metric": metric, "series": series, "variable": var.upper(), **r})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gss_national.json").write_text(json.dumps(out, indent=1))
    print(f"gss: {len(out)} national estimates")


if __name__ == "__main__":
    main()
