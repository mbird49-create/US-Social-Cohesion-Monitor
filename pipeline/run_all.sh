#!/bin/sh
# Weekly refresh: download raw data (skips files already present; HTOPS checks for new waves),
# check the slow sources for newer releases, then rebuild app/data/cohesion.json.
set -e
cd "$(dirname "$0")/.."
RAW=data/raw
PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip -q install pandas pypdf openpyxl; }

get() { [ -s "$2" ] || { mkdir -p "$(dirname "$2")"; echo "fetch $1"; curl -sSL --fail -o "$2" "$1"; }; }

get https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_stata.zip $RAW/gss/GSS_stata.zip
[ -d $RAW/gss/GSS_stata ] || unzip -q $RAW/gss/GSS_stata.zip -d $RAW/gss

CPS=https://www2.census.gov/programs-surveys/cps/datasets
for y in 19 21 23; do get $CPS/20$y/supp/sep${y}pub.csv $RAW/cps/sep${y}pub.csv; done
for y in 21 23; do get $CPS/20$y/supp/sep${y}nrrep.csv $RAW/cps/sep${y}nrrep.csv; done
get $CPS/2019/supp/sep19rep.zip $RAW/cps/sep19rep.zip
[ -d $RAW/cps/sep19rep ] || unzip -q $RAW/cps/sep19rep.zip -d $RAW/cps/sep19rep

get "https://data.humdata.org/dataset/85ee8e10-0c66-4635-b997-79b6fad44c71/resource/ec896b64-c922-4737-b759-e4bd7f73b8cc/download/social_capital_county.csv" $RAW/oi/social_capital_county.csv

cd pipeline
../$PY gss.py
../$PY cps.py
../$PY oi.py
../$PY htops.py
../$PY freshness.py
../$PY build.py

# Publish: commit the rebuilt data and push, which redeploys GitHub Pages.
# A failed push is logged but does not fail the refresh; the next run pushes both weeks.
cd ..
if git rev-parse --git-dir >/dev/null 2>&1; then
  git add app/data/cohesion.json
  if ! git diff --cached --quiet; then
    git commit -q -m "Weekly data refresh $(date +%Y-%m-%d)"
  fi
  if git log origin/main..main --oneline 2>/dev/null | grep -q .; then
    GIT_TERMINAL_PROMPT=0 git push -q origin main && echo "publish: pushed to origin" || echo "publish: PUSH FAILED (will retry next run)"
  else
    echo "publish: nothing new to push"
  fi
fi
