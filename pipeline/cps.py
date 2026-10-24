"""CPS September Civic Engagement & Volunteering supplement (2019, 2021, 2023) -> national and state estimates.

Universe: persons 16+ with a supplement interview (PRSUPINT = 1), self or proxy response.
Weight: PWNRWGT (the Census-prescribed weight for every item used here).
SE: successive-difference replication with the 160 PWNRWGT replicate weights.
Denominator: valid answers only; don't know / refused / no answer are dropped and their share is recorded.
"""
import json

import numpy as np
import pandas as pd

from common import OUT, RAW, STATES, sdr_se, wprop

CPS = RAW / "cps"
YEARS = (2019, 2021, 2023)

# metric id: (variable, positive codes, valid codes)
ITEMS = {
    "cps_talk_neighbors": ("PES4", {1, 2, 3}, {1, 2, 3, 4, 5, 6}),
    "cps_favors_neighbors": ("PES6", {1, 2, 3}, {1, 2, 3, 4, 5, 6}),
    "cps_group_member": ("PES15", {1}, {1, 2}),
    "cps_volunteer": ("PRSUPVOL", {1}, {1, 2}),
    "cps_public_meeting": ("PES12", {1}, {1, 2}),
}


def load_reps(year):
    yy = str(year)[2:]
    if year == 2019:
        path = CPS / "sep19rep" / "cpspb" / "supp" / "data" / "sep19" / "sep19rep.dat"
        widths = [5, 2] + [10] * 161
        names = ["QSTNUM", "OCCURNUM"] + [f"pwnrwgt{i}" for i in range(161)]
        reps = pd.read_fwf(path, widths=widths, names=names)
    else:
        reps = pd.read_csv(CPS / f"sep{yy}nrrep.csv")
    return reps


def load(year):
    yy = str(year)[2:]
    cols = ["QSTNUM", "OCCURNUM", "GESTFIPS", "PRSUPINT", "PWNRWGT"] + [v for v, _, _ in ITEMS.values()]
    path = CPS / f"sep{yy}pub.csv"
    # The 2019 CSV labels the state FIPS column GCFIP (codes match GESTFIPS in the record layout).
    rename = {"GCFIP": "GESTFIPS"} if year == 2019 else {}
    header = pd.read_csv(path, nrows=0).rename(columns=rename).columns
    pub = pd.read_csv(path, usecols=lambda c: rename.get(c, c) in cols).rename(columns=rename)
    assert set(cols) <= set(header)
    pub = pub[(pub.PRSUPINT == 1) & (pub.PWNRWGT > 0)]
    reps = load_reps(year)
    df = pub.merge(reps, on=["QSTNUM", "OCCURNUM"], how="left", validate="one_to_one")
    rep_cols = [f"pwnrwgt{i}" for i in range(1, 161)]
    if df[rep_cols].isna().any().any():
        raise ValueError(f"{year}: persons without replicate weights")
    # The replicate file's base weight must equal PWNRWGT (allowing for implied decimals in the 2019 ASCII file).
    ratio = (df.pwnrwgt0 / df.PWNRWGT).median()
    if not np.isclose(ratio, 1, atol=1e-3):
        if np.isclose(ratio, 10000, rtol=1e-3):
            df[["pwnrwgt0"] + rep_cols] = df[["pwnrwgt0"] + rep_cols] / 10000
        else:
            raise ValueError(f"{year}: replicate base weight does not match PWNRWGT (ratio {ratio})")
    return df, rep_cols


def estimate(g, var, positive, valid, rep_cols):
    v = g[g[var].isin(valid)]
    y = v[var].isin(positive).to_numpy(float)
    w = v.PWNRWGT.to_numpy(float)
    reps = v[rep_cols].to_numpy(float)
    item_nonresponse = float(1 - g.PWNRWGT[g[var].isin(valid)].sum() / g.PWNRWGT.sum())
    return {"value": wprop(y, w), "se": sdr_se(y, w, reps), "n": int(len(v)),
            "item_nonresponse": item_nonresponse}


def main():
    national, state = [], []
    for year in YEARS:
        df, rep_cols = load(year)
        for metric, (var, pos, valid) in ITEMS.items():
            national.append({"metric": metric, "year": year, "variable": var,
                             **estimate(df, var, pos, valid, rep_cols)})
            for fips, g in df.groupby("GESTFIPS"):
                abbr, name = STATES[int(fips)]
                state.append({"metric": metric, "year": year, "fips": int(fips), "abbr": abbr,
                              "state": name, **estimate(g, var, pos, valid, rep_cols)})
        print(f"cps {year}: {len(df)} supplement respondents")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cps_national.json").write_text(json.dumps(national, indent=1))
    (OUT / "cps_state.json").write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
