"""Shared helpers: paths, state names, weighted proportions and their standard errors."""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

STATES = {
    1: ("AL", "Alabama"), 2: ("AK", "Alaska"), 4: ("AZ", "Arizona"), 5: ("AR", "Arkansas"),
    6: ("CA", "California"), 8: ("CO", "Colorado"), 9: ("CT", "Connecticut"), 10: ("DE", "Delaware"),
    11: ("DC", "District of Columbia"), 12: ("FL", "Florida"), 13: ("GA", "Georgia"), 15: ("HI", "Hawaii"),
    16: ("ID", "Idaho"), 17: ("IL", "Illinois"), 18: ("IN", "Indiana"), 19: ("IA", "Iowa"),
    20: ("KS", "Kansas"), 21: ("KY", "Kentucky"), 22: ("LA", "Louisiana"), 23: ("ME", "Maine"),
    24: ("MD", "Maryland"), 25: ("MA", "Massachusetts"), 26: ("MI", "Michigan"), 27: ("MN", "Minnesota"),
    28: ("MS", "Mississippi"), 29: ("MO", "Missouri"), 30: ("MT", "Montana"), 31: ("NE", "Nebraska"),
    32: ("NV", "Nevada"), 33: ("NH", "New Hampshire"), 34: ("NJ", "New Jersey"), 35: ("NM", "New Mexico"),
    36: ("NY", "New York"), 37: ("NC", "North Carolina"), 38: ("ND", "North Dakota"), 39: ("OH", "Ohio"),
    40: ("OK", "Oklahoma"), 41: ("OR", "Oregon"), 42: ("PA", "Pennsylvania"), 44: ("RI", "Rhode Island"),
    45: ("SC", "South Carolina"), 46: ("SD", "South Dakota"), 47: ("TN", "Tennessee"), 48: ("TX", "Texas"),
    49: ("UT", "Utah"), 50: ("VT", "Vermont"), 51: ("VA", "Virginia"), 53: ("WA", "Washington"),
    54: ("WV", "West Virginia"), 55: ("WI", "Wisconsin"), 56: ("WY", "Wyoming"),
}


def wprop(y, w):
    """Weighted proportion of y == 1."""
    return float(np.sum(w * y) / np.sum(w))


def kish_se(y, w):
    """SE of a weighted proportion using Kish's effective n. Ignores clustering, so it understates the SE."""
    p = wprop(y, w)
    n_eff = np.sum(w) ** 2 / np.sum(w ** 2)
    return float(np.sqrt(p * (1 - p) / n_eff))


def linearized_se(y, w, strata, psu):
    """Taylor-linearized SE of a weighted proportion under a stratified cluster design (with-replacement PSUs)."""
    p = wprop(y, w)
    z = w * (y - p) / np.sum(w)
    total = 0.0
    for h in np.unique(strata):
        in_h = strata == h
        psus = np.unique(psu[in_h])
        n_h = len(psus)
        if n_h < 2:
            continue
        zt = np.array([z[in_h & (psu == i)].sum() for i in psus])
        total += n_h / (n_h - 1) * np.sum((zt - zt.mean()) ** 2)
    return float(np.sqrt(total))


def sdr_se(y, w, reps):
    """CPS successive-difference replication SE: var = 4/R * sum_r (theta_r - theta)^2."""
    p = wprop(y, w)
    thetas = (reps * y[:, None]).sum(axis=0) / reps.sum(axis=0)
    return float(np.sqrt(4 / reps.shape[1] * np.sum((thetas - p) ** 2)))
