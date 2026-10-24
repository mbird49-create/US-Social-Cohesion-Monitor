"""Combine processed estimates with the metric registry into app/data/cohesion.json.

The registry is the single place that says what each metric measures, what it does not, and where it comes from.
New sources (including CAV's own survey) are added by appending registry entries and estimate rows in the same shape.
Each run also compares the newest data period per metric with the previous build and logs what changed.
"""
import json
from datetime import date, datetime

from common import OUT, ROOT

GSS_URL = "https://gss.norc.org/us/en/gss/get-the-data.html"
CPS_URL = "https://www.census.gov/data/datasets/time-series/demo/cps/cps-supp_cps-repwgt/cps-volunteer.html"
OI_URL = "https://data.humdata.org/dataset/social-capital-atlas"
HTOPS_URL = "https://www.census.gov/data/experimental-data-products/household-trends-and-outlook-pulse-survey.html"
DEST = ROOT / "app" / "data" / "cohesion.json"
LOG = OUT / "refresh_log.json"

GSS_COMMON = {
    "source": "General Social Survey (NORC), cumulative file 1972-2024, release 3a",
    "source_key": "gss",
    "source_url": GSS_URL,
    "geography": ["national"],
    "universe": "US adults 18+ living in households (English or Spanish speakers since 2006)",
    "weight": "WTSSPS (person post-stratification weight)",
    "se_method": "Taylor linearization on VSTRAT/VPSU; Kish effective-n where design codes are absent (1972-1973)",
    "state_gap": ("The public GSS file has no state identifiers (they are restricted-use), and the sample is not designed "
                  "for state estimates."),
    "series_note": ("Two series are shown and never joined. 'Interviewer' = in-person or phone interviews (TRUST etc.). "
                    "'Web' = web self-completion without a volunteered 'depends' option (TRUSTNV etc.), 2021-2024. "
                    "In years with both, the web series runs several points higher, so the 2018-2021 change "
                    "cannot be read as a real change."),
}

CPS_COMMON = {
    "source": "Current Population Survey, September Civic Engagement and Volunteering Supplement (Census Bureau / AmeriCorps)",
    "source_key": "cps",
    "source_url": CPS_URL,
    "geography": ["national", "state"],
    "universe": "Civilian non-institutional persons 16+ with a supplement interview (self or proxy response)",
    "weight": "PWNRWGT (supplement non-response weight)",
    "se_method": "Successive-difference replication, 160 PWNRWGT replicate weights",
    "years_note": "Asked with identical wording in 2019, 2021 and 2023. Earlier supplements used different items and are not included.",
}

OI_COMMON = {
    "source": "Opportunity Insights Social Capital Atlas (Chetty et al. 2022, Nature), county file",
    "source_key": "oi",
    "source_url": OI_URL,
    "geography": ["national", "state"],
    "universe": "Facebook users aged 25-44 in the US with sufficient friends and location data, 2018-2019",
    "state_tag": {"tag": "uncertain", "text": "The state values are this app's population-weighted aggregation of county estimates. Opportunity Insights does not publish state figures."},
}

HTOPS_COMMON = {
    "source": "Household Trends and Outlook Pulse Survey (Census Bureau), published national tables",
    "source_key": "htops",
    "source_url": HTOPS_URL,
    "geography": ["national"],
    "universe": "Adults 18+ in US households",
    "weight": "Census person weights, as applied in the published tables",
    "se_method": "Census published SE tables; summed categories ignore covariance (approximate)",
    "state_gap": ("HTOPS publishes national, regional and top-10 metro tables only, so there are no state estimates. "
                  "Regional tables could be added."),
    "years_note": ("Only waves from March 2026 on are used: that is when HTOPS changed from a longitudinal to a "
                   "cross-sectional design. Waves are about two months apart and not every topic is asked in every wave."),
}

HTOPS_TAGS = [
    {"tag": "uncertain", "text": "Census labels HTOPS data experimental. The sample is a recruited panel of about 136,000 households per wave, with low response rates."},
    {"tag": "uncertain", "text": "The published answer categories differ between waves (some are merged in July 2026). Census notes that some variables were recoded for disclosure avoidance. Check the data dictionaries before reading a change between waves as real."},
]

METRICS = [
    # ---- generalized trust ----
    {
        "id": "gss_trust", "dimension": "trust", "headline": True, **GSS_COMMON,
        "label": "Say most people can be trusted",
        "plain": "of adults say most people can be trusted",
        "wording": "Generally speaking, would you say that most people can be trusted or that you can't be too careful in dealing with people?",
        "response_cut": "Share answering 'most people can be trusted'. 'Depends' stays in the denominator.",
        "measures": "Generalized trust in unspecified others: an attitude reported to an interviewer or on a web form.",
        "does_not_measure": "Trust in neighbors, institutions or specific groups. Trusting behavior. Any state or local variation.",
        "tags": [{"tag": "uncertain", "text": "The item is known to be sensitive to mode, question order and what 'most people' brings to mind for the respondent."}],
    },
    {
        "id": "gss_fair", "dimension": "trust", **GSS_COMMON,
        "label": "Say most people would try to be fair",
        "plain": "say most people would try to be fair",
        "wording": "Do you think most people would try to take advantage of you if they got a chance, or would they try to be fair?",
        "response_cut": "Share answering 'would try to be fair'. 'Depends' stays in the denominator.",
        "measures": "Expectations about other people's fairness toward oneself.",
        "does_not_measure": "Fair treatment actually experienced, or institutional fairness.",
        "tags": [],
    },
    {
        "id": "gss_helpful", "dimension": "trust", **GSS_COMMON,
        "label": "Say people mostly try to be helpful",
        "plain": "say people mostly try to be helpful",
        "wording": "Would you say that most of the time people try to be helpful, or that they are mostly just looking out for themselves?",
        "response_cut": "Share answering 'try to be helpful'. 'Depends' stays in the denominator.",
        "measures": "Expectations about other people's helpfulness.",
        "does_not_measure": "Help actually given or received.",
        "tags": [],
    },
    # ---- bonding ties ----
    {
        "id": "htops_support", "dimension": "bonding", "headline": True, **HTOPS_COMMON,
        "label": "Usually or always get the social and emotional support they need",
        "plain": "of adults usually or always get the social and emotional support they need",
        "wording": "Census table header: 'Obtains social and emotional support'. See the wave questionnaire for the full wording.",
        "response_cut": "'Always' or 'Usually'. 'Did not report' is excluded.",
        "measures": "Self-reported adequacy of emotional support: a measure of the quality of close ties.",
        "does_not_measure": "Who provides the support (family, friends, community) or whether the ties cross group lines.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "htops_inperson", "dimension": "bonding", **HTOPS_COMMON,
        "label": "Get together in person with loved ones or close network at least weekly",
        "plain": "see loved ones or their close network in person at least once a week",
        "wording": "Census table header: 'Gets together in person with loved ones or close social network'.",
        "response_cut": "'1 or 2', '3 or 4' or '5 or more' times a week. 'Did not report' is excluded.",
        "measures": "How often people see their close ties in person.",
        "does_not_measure": "Quality of contact, or contact by phone or video (published separately and not shown).",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "cps_talk_neighbors", "dimension": "bonding", **CPS_COMMON,
        "label": "Talked with or spent time with neighbors at least a few times a month",
        "plain": "talk with neighbors at least a few times a month",
        "wording": "In the past 12 months, how often did you have a conversation or spend time with your neighbors?",
        "response_cut": "'Basically every day', 'a few times a week' or 'a few times a month' (codes 1-3 of 6).",
        "measures": "Self- or proxy-reported frequency of contact with neighbors.",
        "does_not_measure": "Quality or warmth of the contact, felt belonging, or trust in neighbors.",
        "tags": [{"tag": "uncertain", "text": "Neighbor ties are classed as bonding here (local, frequent ties), but neighbors may differ in class, race or politics, so these ties can also bridge."},
                 {"tag": "uncertain", "text": "Some answers are proxy reports by another household member, who may not know how often the person talks to neighbors."},
                 {"tag": "uncertain", "text": "The cut point (a few times a month or more) is this app's choice. AmeriCorps uses 'a few times a week or more' for 'frequently'."}],
    },
    {
        "id": "cps_favors_neighbors", "dimension": "bonding", **CPS_COMMON,
        "label": "Exchanged favors with neighbors at least a few times a month",
        "plain": "exchange favors with neighbors at least a few times a month",
        "wording": "In the past 12 months, how often did you and your neighbors do favors for each other such as house sitting, watching each other's children, lending tools, and other things to help each other?",
        "response_cut": "Codes 1-3 of 6, the same cut as the conversation item.",
        "measures": "Reported reciprocal practical help between neighbors.",
        "does_not_measure": "Help within families or between friends who are not neighbors.",
        "tags": [{"tag": "uncertain", "text": "Proxy reporting, and the bonding/bridging classification, as for the conversation item."}],
    },
    {
        "id": "oi_clustering", "dimension": "bonding", **OI_COMMON,
        "label": "Friendship network clustering",
        "plain": "of a person's friend pairs are also friends with each other",
        "weight": "Counties weighted by pop2018",
        "se_method": "No SE published for this measure",
        "wording": "Not a survey item. It is computed from Facebook friendship networks.",
        "response_cut": "Average share of a person's friend pairs who are also friends with each other.",
        "measures": "Density of friendship networks: how tightly knit people's circles are.",
        "does_not_measure": "Whether the ties are supportive, or whether they sit within or across social groups.",
        "tags": [OI_COMMON["state_tag"],
                 {"tag": "uncertain", "text": "Dense networks can mean strong communities or closed ones. Higher is not simply better."}],
    },
    {
        "id": "oi_support_ratio", "dimension": "bonding", **OI_COMMON,
        "label": "Friendship support ratio",
        "plain": "of friendships are embedded in at least one shared friend",
        "weight": "Counties weighted by pop2018",
        "se_method": "No SE published for this measure",
        "wording": "Not a survey item. It is computed from Facebook friendship networks.",
        "response_cut": "Share of friendships within the county where the two friends have at least one other friend in common.",
        "measures": "How embedded friendships are in mutual networks, a structural proxy for support.",
        "does_not_measure": "Support actually given or received.",
        "tags": [OI_COMMON["state_tag"]],
    },
    # ---- bridging ties ----
    {
        "id": "oi_economic_connectedness", "dimension": "bridging", "headline": True, **OI_COMMON,
        "label": "Economic connectedness (cross-class friendship)",
        "plain": "economic connectedness: 1.0 would mean friendships fully mixed across the income line",
        "weight": "Counties weighted by num_below_p50 (estimated number of below-median-SES people)",
        "se_method": "County SEs combined assuming independence (approximate)",
        "wording": "Not a survey item. It is computed from Facebook friendship networks.",
        "response_cut": "2 x the average share of above-median-SES friends among below-median-SES people. 1.0 = no class segregation in friendships, below 1 = fewer cross-class friends than an even mix would give.",
        "measures": "How often lower-income people's friendships reach across the income line.",
        "does_not_measure": "Ties across race, religion or party. Friendship quality. People not on Facebook. Any change over time (one snapshot only).",
        "tags": [OI_COMMON["state_tag"],
                 {"tag": "uncertain", "text": "The sample covers Facebook users aged 25-44 only. OI reweights for representativeness, but platform selection bias remains."}],
    },
    # ---- civic participation ----
    {
        "id": "htops_clubs", "dimension": "participation", "headline": True, **HTOPS_COMMON,
        "label": "Attended a club or organization meeting in the last 12 months",
        "plain": "attended a club or organization meeting in the past year",
        "wording": "Census table header: 'Attended meetings of clubs or organizations in the last 12 months'.",
        "response_cut": "Any attendance (1 or more times). 'Did not report' is excluded.",
        "measures": "Any participation in organized group life over the past year.",
        "does_not_measure": "How often or how actively people take part, or what kind of group it is.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "cps_group_member", "dimension": "participation", **CPS_COMMON,
        "label": "Belonged to any group, organization or association",
        "plain": "belong to a group, organization or association",
        "wording": "In the past 12 months, did you belong to any groups, organizations, or associations?",
        "response_cut": "'Yes'.",
        "measures": "Any reported formal group membership.",
        "does_not_measure": "How active the membership is, whether the group mixes social or political lines, or informal networks.",
        "tags": [],
    },
    {
        "id": "cps_volunteer", "dimension": "participation", **CPS_COMMON,
        "label": "Formally volunteered through an organization",
        "plain": "volunteered through an organization in the past year",
        "wording": "Census recode PRSUPVOL: 'yes' to 'spend any time volunteering for any organization or association' or to the follow-up prompt about infrequent or children's activities.",
        "response_cut": "PRSUPVOL = 1 (volunteer). Matches AmeriCorps' published formal volunteering rate.",
        "measures": "Formal volunteering through an organization in the past 12 months.",
        "does_not_measure": "Informal helping (see the favors item) or hours volunteered.",
        "tags": [{"tag": "uncertain", "text": "PRSUPVOL has no missing category: people who did not answer are coded 'not a volunteer'."},
                 {"tag": "uncertain", "text": "2021 fieldwork fell during COVID-19, when many organizations had paused in-person volunteering."}],
    },
    {
        "id": "cps_public_meeting", "dimension": "participation", **CPS_COMMON,
        "label": "Attended a public meeting about a local issue",
        "plain": "attended a public meeting about a local issue",
        "wording": "In the past 12 months, did you attend a public meeting, such as a zoning or school board meeting, to discuss a local issue?",
        "response_cut": "'Yes'.",
        "measures": "Participation in local deliberative civic life.",
        "does_not_measure": "Whether the meeting brought different groups together, or what the person did there.",
        "tags": [{"tag": "uncertain", "text": "2021 fieldwork fell during COVID-19, so many meetings were held online or not at all."}],
    },
    # ---- individual and family well-being ----
    {
        "id": "htops_lonely", "dimension": "wellbeing", "headline": True, **HTOPS_COMMON,
        "label": "Usually or always feel lonely",
        "plain": "of adults usually or always feel lonely",
        "wording": "Census table header: 'Feelings of loneliness'.",
        "response_cut": "'Always' or 'Usually' (shown as one merged category in July 2026). 'Did not report' is excluded.",
        "measures": "Frequent self-reported loneliness.",
        "does_not_measure": "Objective isolation (living alone, number of contacts), or loneliness that is occasional.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "htops_anxiety", "dimension": "wellbeing", **HTOPS_COMMON,
        "label": "Felt nervous, anxious or on edge on more than half the days (last 2 weeks)",
        "plain": "felt nervous, anxious or on edge on more than half of the last 14 days",
        "wording": "Census table header: 'Frequency of feeling nervous, anxious, or on edge in the last 2 weeks'.",
        "response_cut": "'More than half the days' or 'Nearly every day'.",
        "measures": "Frequent anxiety symptoms, from one item.",
        "does_not_measure": "Clinical anxiety disorder. The standard GAD-2 screen needs two items summed, which the published tables do not allow.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "htops_depression", "dimension": "wellbeing", **HTOPS_COMMON,
        "label": "Felt down, depressed or hopeless on more than half the days (last 2 weeks)",
        "plain": "felt down, depressed or hopeless on more than half of the last 14 days",
        "wording": "Census table header: 'Frequency of feeling down, depressed, or hopeless in the last 2 weeks'.",
        "response_cut": "'More than half the days' or 'Nearly every day'.",
        "measures": "Frequent depressive symptoms, from one item.",
        "does_not_measure": "Clinical depression. The standard PHQ-2 screen needs two items summed.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "htops_food_insufficient", "dimension": "wellbeing", **HTOPS_COMMON,
        "label": "Live in a household that sometimes or often didn't have enough to eat (last 7 days)",
        "plain": "live in a household that sometimes or often didn't have enough to eat in the past week",
        "wording": "Census table header: 'Food sufficiency in the last 7 days' (asked about the household).",
        "response_cut": "'Sometimes not enough to eat' or 'Often not enough to eat'.",
        "measures": "Household food insufficiency, reported by an adult: a measure of family material well-being.",
        "does_not_measure": "Diet quality, or hardship other than food.",
        "tags": HTOPS_TAGS,
    },
    {
        "id": "gss_very_happy", "dimension": "wellbeing", **GSS_COMMON,
        "series_note": ("Two series are shown and never joined. 'Interviewer' = in-person or phone; 'Web' = web self-completion (2021-2024). "
                        "Respondents were not randomly assigned to mode, so the gap mixes mode effects with differences in who answered by web."),
        "label": "Say they are very happy",
        "plain": "say they are very happy",
        "wording": "Taken all together, how would you say things are these days - would you say that you are very happy, pretty happy, or not too happy?",
        "response_cut": "'Very happy'.",
        "measures": "Global self-rated happiness.",
        "does_not_measure": "Life satisfaction, purpose, or family well-being.",
        "tags": [],
    },
]

DIMENSIONS = [
    {"id": "bonding", "label": "Bonding ties", "short": "within groups",
     "definition": "Strength, quality and density of close ties within families, friendship circles and neighborhoods."},
    {"id": "bridging", "label": "Bridging ties", "short": "between groups",
     "definition": "Social ties that cross lines of class, race, religion or party."},
    {"id": "participation", "label": "Civic participation", "short": "group and public life",
     "definition": "Membership, volunteering and taking part in organized and local public life."},
    {"id": "trust", "label": "Generalized trust", "short": "trust in others",
     "definition": "Whether people expect unspecified others to be trustworthy, fair and helpful."},
    {"id": "wellbeing", "label": "Individual and family well-being", "short": "how people are doing",
     "definition": "Emotional and material well-being of individuals and the households they live in."},
    {"id": "belonging", "label": "Belonging", "short": "feeling part of it",
     "definition": "A felt sense of being part of one's community and the country."},
]

GAPS = [
    {"dimension": "belonging", "text": "No public source gives repeated measures of felt belonging. Neighborhood contact is a behavior and is not used as a stand-in. Candidate for CAV's own survey."},
    {"dimension": None, "text": "No source in the app is weekly. The freshest (HTOPS) arrives about every two months, and most others every two years. The weekly page is a weekly check for new data, not a weekly measurement."},
    {"dimension": "trust", "text": "No state-level generalized trust. The 2019-2023 CPS supplements have no trust item, and the public GSS file has no state identifiers. [uncertain] Earlier CPS supplements may have had a neighbor-trust item. Not checked here."},
    {"dimension": "trust", "text": "Institutional trust (government, media, science) is a separate construct and is not included yet."},
    {"dimension": "bridging", "text": "Only cross-class ties are measured. Cross-race, cross-religion and cross-party ties have no comparable public source here."},
    {"dimension": "bridging", "text": "All bridging and network-density data are a single 2018-2019 snapshot, so there is no trend."},
    {"dimension": "wellbeing", "text": "Family well-being is covered only by food sufficiency. Child well-being, family relationships and economic security beyond food are not included."},
    {"dimension": None, "text": "The JEC Social Capital Index (2018, state and county) is not included: the JEC site blocks automated downloads."},
    {"dimension": None, "text": "No composite cohesion score. The dimensions measure different constructs and are reported separately on purpose."},
]


def period(source, row):
    """Label and approximate end date of the data collection behind a national row."""
    if source == "htops":
        start, end = (datetime.strptime(row[k], "%Y-%m-%d") for k in ("period_start", "period_end"))
        return f"Collected {start:%b} {start.day} to {end:%b} {end.day}, {end.year}", row["period_end"]
    if source == "cps":
        return f"September {row['year']}", f"{row['year']}-09-30"
    if source == "oi":
        return "Friendships as of 2018-2019 (released 2022)", "2019-12-31"
    return f"Fielded {row['year']}", f"{row['year']}-12-31"  # GSS fieldwork dates vary; year end is an approximation


def load(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else []


def latest_by_metric(national):
    out = {}
    for r in national:
        if "period_end" not in r:
            return {}  # build from before period tracking existed: treat as no baseline
        if r["period_end"] > out.get(r["metric"], {}).get("period_end", ""):
            out[r["metric"]] = {"period_end": r["period_end"], "value": r["value"]}
    return out


def main():
    src = {m["id"]: m["source_key"] for m in METRICS}
    keep = ("metric", "series", "year", "value", "se", "n", "item_nonresponse", "wave")
    national = []
    for name, default_series in (("gss_national.json", None), ("cps_national.json", "main"),
                                 ("oi_national.json", "main"), ("htops_national.json", None)):
        for r in load(name):
            row = {"series": default_series, **{k: r[k] for k in keep if k in r}}
            row["period_label"], row["period_end"] = period(src[r["metric"]], r)
            national.append(row)
    state = []
    for r in load("cps_state.json"):
        state.append({k: r[k] for k in ("metric", "year", "fips", "abbr", "state", "value", "se", "n")})
    for r in load("oi_state.json"):
        state.append({k: r[k] for k in ("metric", "year", "fips", "abbr", "state", "value", "se", "n_counties")})

    ids = {m["id"] for m in METRICS}
    unknown = {r["metric"] for r in national + state} - ids
    if unknown:
        raise ValueError(f"estimates without registry entries: {unknown}")
    for m in METRICS:
        m["years"] = sorted({r["year"] for r in national + state if r["metric"] == m["id"]})
        m.pop("state_tag", None)

    # What changed since the previous build
    today = date.today().isoformat()
    now = latest_by_metric(national)
    before = latest_by_metric(json.loads(DEST.read_text())["national"]) if DEST.exists() else {}
    labels = {m["id"]: m["label"] for m in METRICS}
    changes = [{"metric": k, "label": labels[k], "period_end": v["period_end"]}
               for k, v in now.items() if before and v["period_end"] > before.get(k, {}).get("period_end", "")]
    log = load("refresh_log.json")
    log.append({"date": today, "new_data": changes})
    LOG.write_text(json.dumps(log[-104:], indent=1))  # keep about two years of weekly runs
    last_new = next((e for e in reversed(log) if e["new_data"]), None)

    freshness = json.loads((OUT / "freshness.json").read_text()) if (OUT / "freshness.json").exists() else None
    out = {"generated": today, "refresh": {"date": today, "new_data": changes, "last_new_data": last_new,
                                           "freshness": freshness},
           "dimensions": DIMENSIONS, "metrics": METRICS, "gaps": GAPS, "national": national, "state": state}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(out, separators=(",", ":")))
    print(f"build: {len(national)} national + {len(state)} state rows; new data this run: {len(changes)}")


if __name__ == "__main__":
    main()
