# US Social Cohesion Monitor (MVP)

A static web dashboard giving a weekly snapshot of social cohesion in the US: bonding ties (within groups), bridging
ties (between groups), civic participation, generalized trust, and individual and family well-being, with belonging
marked as a gap. The "This week" page shows the newest figure for each dimension and how old its data is.
"Explore" has trends, state maps and full definitions. There is deliberately no composite score.

**Weekly means a weekly check, not weekly data.** The freshest source (Census HTOPS) is about every two months,
and the others every two years or less often. See `docs/DATA_SOURCES.md`.

## View it

```bash
cd ~/social-cohesion/app && python3 -m http.server 8765
```

Then open http://localhost:8765. It needs internet access for d3 and the US state map, which load from jsdelivr.
The `app/` folder is fully static, so it can be copied as-is to any web host (e.g. thecav.org).

## Weekly refresh

```bash
~/social-cohesion/pipeline/run_all.sh
```

Run this once a week. It downloads new HTOPS waves automatically, checks GSS, CPS and Opportunity Insights for newer
releases (flagged on the page for review, not added automatically), logs what changed in `data/processed/refresh_log.json`,
and downloads any missing raw files (about 1.4 GB unpacked, kept in `data/raw/`), recomputes every estimate and writes
`app/data/cohesion.json`. Once the files are downloaded, a rebuild takes about 10 seconds.

### Scheduled run

A launchd agent runs this script every **Monday at 07:00** (local time):
`~/Library/LaunchAgents/org.thecav.social-cohesion.weekly.plist`. Output goes to `logs/weekly.log`.
If the Mac is asleep at that time, the run happens when it next wakes. If it is shut down, that week's run is skipped.
The job updates only the local `app/` folder. A copy hosted elsewhere (e.g. thecav.org) has to be re-uploaded.

```bash
launchctl kickstart gui/$(id -u)/org.thecav.social-cohesion.weekly
```
runs it now. To turn it off:
```bash
launchctl bootout gui/$(id -u)/org.thecav.social-cohesion.weekly
```

## Layout

| Path | What it is |
|---|---|
| `pipeline/gss.py` | GSS -> national trust, fairness and helpfulness, two mode series |
| `pipeline/cps.py` | CPS Civic Engagement & Volunteering supplement -> national + state, replicate-weight SEs |
| `pipeline/oi.py` | Opportunity Insights county file -> state economic connectedness, clustering, support ratio (derived) |
| `pipeline/htops.py` | Census HTOPS published tables -> national support, contact, loneliness, anxiety, depression, food sufficiency |
| `pipeline/freshness.py` | Weekly release check for the slow sources |
| `pipeline/build.py` | **Metric registry** (what each metric measures and does not, wording, cut, universe, weight, tags), gaps list, final JSON |
| `app/` | Dashboard (HTML/CSS/JS, d3 7.9.0, no build step) |
| `docs/DATA_SOURCES.md` | Sources used and their limits |

## Adding a source (including CAV's own survey)

1. Write `pipeline/<source>.py` that outputs rows shaped like the others:
   `{metric, year, value, se, n}` for national (plus `series`) and `{metric, year, fips, abbr, state, value, se, n}` for state.
2. Add one registry entry per metric to `METRICS` in `build.py` (every field the existing entries have, including
   `does_not_measure` and `tags`), and load the new rows in `build.main()`.
3. `build.py` refuses estimates that have no registry entry, so a number can't appear without its definition.

For CAV's own survey, the obvious first target is the **belonging** dimension, which has no public measure (see the gaps).
