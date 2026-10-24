# Data sources and their limits

Updated 2026-10-23. Every figure in the app comes from one of the four sources below. Claims are descriptive only.

## How fresh is "weekly"?

**[gap] No source in this app measures cohesion weekly.** The page is *checked and rebuilt* weekly
(`pipeline/run_all.sh`). Each figure shows its collection period and age, and the This week page says whether anything new arrived.

| Source | Newest data used | Cadence | Typical lag |
|---|---|---|---|
| Census HTOPS | Jul 15 – Aug 3, 2026 | About every 2 months (not every topic every wave) | A few weeks after collection |
| GSS | 2024 | Every 2 years | 6–12 months |
| CPS Civic Engagement supplement | September 2023 | Every 2 years | About a year (Sept 2025 microdata not yet out) |
| Opportunity Insights | 2018–2019 friendships | One-off release (2022) | — |

A true weekly reading would need CAV's own repeated survey, which the user deferred. HTOPS waves are downloaded
automatically. A newer GSS, CPS or OI release is only *flagged* (Source check table), because wording and coding
must be reviewed before a new release is added.

## 1. Census Household Trends and Outlook Pulse Survey (HTOPS), published national tables, 2026 waves

- **Used for:** Emotional support and in-person get-togethers (bonding); club or organization meetings (participation); frequent loneliness, anxiety and depression symptoms, and household food insufficiency (well-being). National only.
- **Download:** `health*.xlsx` and `food*.xlsx`, plus their `_se` tables, from www2.census.gov/programs-surveys/demo/tables/hhp/YYYY/YYMM/. Each wave's collection dates are read from its Census table page.
- **Estimate:** Share of adults 18+ in the positive categories among those who answered ("Did not report" excluded). Tables are matched by question header text, because table numbers change between waves.
- **SE:** From Census's SE tables. Where categories are summed, covariance is ignored, which is approximate.
- **Limits**
  - **[uncertain]** Census labels HTOPS experimental. It is a recruited panel of about 136,000 households per wave, with low response rates.
  - **[uncertain]** Only waves from March 2026 on are used, because HTOPS switched from a longitudinal to a cross-sectional design that month. The May 2026 wave has no health tables. Census corrected a weighting error in the March and May 2026 files in July 2026; the pipeline downloads the current tables.
  - **[uncertain]** The answer categories differ between waves. Loneliness was published as five options in March and with "Always or Usually" merged in July, and Census notes some disclosure-avoidance recoding. The loneliness change from March to July (5.8% to 9.0%) may not be real, so the app shows the waves as separate points with no connecting line.
  - **[uncertain]** Anxiety and depression are single items, not the standard two-item GAD-2 or PHQ-2 screens, which can't be computed from the tables.
  - **[uncertain]** Item wording comes from the table headers. The full questionnaire wording should be checked against each wave's questionnaire.
  - **[gap]** There are no state tables, only national, regional and top-10 metro.
  - The earlier Household Pulse Survey (2020–Sept 2024, on data.cdc.gov) had similar items, but it is a different design and is not joined to HTOPS.

## 2. General Social Survey (NORC), cumulative file 1972–2024, release 3a

- **Used for:** Generalized trust (TRUST), expected fairness (FAIR), expected helpfulness (HELPFUL), and happiness (HAPPY, "very happy"). National only.
- **Download:** `GSS_stata.zip` from gss.norc.org (file `gss7224_r3a.dta`).
- **Estimate:** Weighted share giving the positive answer. "Depends" stays in the denominator for the trust items; DK and no answer are dropped. Weight `WTSSPS`.
- **SE:** Taylor linearization on `VSTRAT`/`VPSU`. For 1972–73, which have no design codes, Kish effective n is used, which understates the SE.
- **Limits**
  - **[uncertain] Mode break.** 2021 was web-only, and 2022 and 2024 mixed modes. The trust items use the GSS's own split: `TRUST` (interviewer) and `TRUSTNV` (web, no volunteered "depends"). In 2022–24 the web series runs 4–11 points higher. HAPPY has no such split, so it is divided by `MODE` (in-person or phone vs. web). Respondents weren't randomly assigned a mode, so that gap mixes mode effects with differences in who answered online.
  - **[uncertain]** A data "age" for the GSS is measured from 31 December of the survey year. Fieldwork dates vary.
  - **[gap]** The public file has no state identifiers.
  - Items are asked on a subset of ballots, so the yearly n is about 900–2,500. Several years are missing.

## 3. CPS September Civic Engagement and Volunteering Supplement (Census Bureau for AmeriCorps), 2019, 2021, 2023

- **Used for:** Talking with neighbors and exchanging favors with neighbors (bonding); group membership, formal volunteering and attending public meetings (participation). National and state.
- **Download:** `sepYYpub.csv` plus the non-response replicate weights (`sepYYnrrep.csv`; 2019 `sep19rep.dat`, fixed width) from www2.census.gov.
- **Estimate:** Universe is persons 16+ with a supplement interview (`PRSUPINT = 1`). Weight `PWNRWGT`. Frequency items count "a few times a month or more".
- **SE:** Successive-difference replication, 160 replicates.
- **Check:** National volunteering comes out at 30.0% / 23.2% / 28.3%, which matches AmeriCorps' published rates.
- **Limits**
  - **[uncertain]** Neighbor ties are classed as *bonding* by convention, but neighbors may differ in class, race or politics, so these ties can also bridge.
  - **[uncertain]** The data include proxy responses (another household member answering), the cut point is this app's choice, 2021 fieldwork fell during COVID-19, and PRSUPVOL codes non-answers as "not a volunteer".
  - The 2019 CSV labels the state FIPS column `GCFIP`. The pipeline renames it after checking that the codes match FIPS.
  - State samples range from about 360 to 4,400 respondents, and most pairs of state intervals overlap.

## 4. Opportunity Insights Social Capital Atlas (Chetty et al. 2022, *Nature*), county file

- **Used for:** Economic connectedness (bridging); network clustering and support ratio (bonding, network density). National and state.
- **Download:** `social_capital_county.csv` from data.humdata.org/dataset/social-capital-atlas.
- **Estimate:** **State values are derived here; OI does not publish them.** EC is weighted by `num_below_p50`, and clustering and support ratio by `pop2018`. EC SEs combine county SEs as if independent (approximate). OI publishes no SEs for clustering or support ratio.
- **Limits**
  - **[uncertain]** The data come from Facebook users aged 25–44 in 2018–2019. It is one snapshot, so there is no trend.
  - **[uncertain]** High clustering can mean tight-knit or closed communities, so higher is not simply better.
  - **[gap]** Only cross-class bridging is measured, not cross-race, cross-religion or cross-party ties.

## Not included, and why

- **[gap] Belonging:** no public repeated measure. This is the main candidate for CAV's own survey.
- **[gap] Family well-being beyond food:** child well-being and family relationships are not covered. HTOPS also publishes housing and spending tables, which could be added.
- **[gap] Institutional trust:** a separate construct. The GSS confidence items could be added.
- **JEC Social Capital Index (2018):** the site blocks automated downloads.
- **Gallup:** no open microdata or reusable license.
