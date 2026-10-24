// US Social Cohesion Monitor: renders app/data/cohesion.json (built by pipeline/build.py).
const ATLAS_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json";
const SERIES_LABEL = { interviewer: "Interviewer (in-person / phone)", web_nv: "Web self-completion", web: "Web self-completion", main: "Estimate" };
const SERIES_VAR = { interviewer: "--series-1", web_nv: "--series-2", web: "--series-2", main: "--series-1" };
const Z = 1.96;

const state = { data: null, atlas: null, metric: null, year: null, sv: "map" };
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const isIndex = (m) => m.id === "oi_economic_connectedness";
const fmt = (m, v) => (v == null ? "n/a" : isIndex(m) ? d3.format(".2f")(v) : d3.format(".1%")(v));
const fmtCI = (m, r) => (r.se == null ? "SE not available" : `95% CI ${fmt(m, r.value - Z * r.se)} to ${fmt(m, r.value + Z * r.se)}`);
const tip = d3.select("#tooltip");
const parseDate = d3.utcParse("%Y-%m-%d");
const fmtDate = d3.utcFormat("%b %-d, %Y");

function ageText(periodEnd, asOf) {
  const days = (parseDate(asOf) - parseDate(periodEnd)) / 864e5;
  if (days < 0) return "current";
  if (days < 7 * 26) return `about ${Math.max(1, Math.round(days / 7))} weeks old`;
  if (days < 365 * 2) return `about ${Math.round(days / 30.4)} months old`;
  return `about ${Math.round(days / 365.25)} years old`;
}
const isFresh = (periodEnd, asOf) => (parseDate(asOf) - parseDate(periodEnd)) / 864e5 < 7 * 26;

// Newest national row for a metric; for multi-series metrics, the interviewer series is the headline.
function latestRow(metricId) {
  const rows = state.data.national.filter((r) => r.metric === metricId);
  const pref = rows.some((r) => r.series === "interviewer") ? rows.filter((r) => r.series === "interviewer") : rows;
  return d3.greatest(pref, (r) => r.period_end);
}

function showView(name) {
  d3.selectAll(".tabs button").attr("aria-selected", function () { return this.dataset.view === name; });
  d3.selectAll(".view").attr("hidden", function () { return this.id === name ? null : true; });
  try { history.replaceState(null, "", name === "explore" && state.metric ? `#${state.metric.id}` : location.pathname); } catch (e) { /* ignore */ }
  if (name === "explore" && state.metric) renderMetric();
}

function showTip(event, html) {
  tip.html(html).attr("hidden", null);
  const { innerWidth: W } = window, box = tip.node().getBoundingClientRect();
  let x = event.clientX + 14, y = event.clientY + 14;
  if (x + box.width > W - 8) x = event.clientX - box.width - 14;
  if (y + box.height > window.innerHeight - 8) y = event.clientY - box.height - 14;
  tip.style("left", `${x}px`).style("top", `${y}px`);
}
const hideTip = () => tip.attr("hidden", true);

function tagsHTML(tags) {
  return tags.map((t) => `<div class="tagline"><span class="tag ${t.tag}">${t.tag}</span>${t.text}</div>`).join("");
}

// ---------- navigation ----------
function renderNav() {
  const { dimensions, metrics, gaps } = state.data;
  const nav = d3.select("#metric-nav").html("");
  for (const dim of dimensions) {
    nav.append("h4").text(dim.label);
    const ms = metrics.filter((m) => m.dimension === dim.id);
    for (const m of ms) {
      nav.append("button").attr("data-id", m.id).text(m.label).on("click", () => selectMetric(m.id));
    }
    if (!ms.length) {
      const g = gaps.find((x) => x.dimension === dim.id);
      nav.append("div").attr("class", "gapnote").html(`<span class="tag gap">gap</span>No measure yet${g ? "" : ""}`);
    }
  }
}

function selectMetric(id) {
  const m = state.data.metrics.find((x) => x.id === id);
  state.metric = m;
  d3.selectAll("#metric-nav button").attr("aria-current", function () { return this.dataset.id === id; });
  const years = [...new Set(state.data.state.filter((r) => r.metric === id).map((r) => r.year))].sort();
  state.year = years.at(-1) ?? null;
  d3.select("#year-select").html("").selectAll("option").data(years).join("option")
    .attr("value", (d) => d).property("selected", (d) => d === state.year).text((d) => d);
  if (!document.querySelector("#explore").hidden) {
    try { history.replaceState(null, "", `#${id}`); } catch (e) { /* ignore */ }
  }
  renderMetric();
}

// ---------- metric panel ----------
function renderMetric() {
  const m = state.metric;
  hideTip();
  const dim = state.data.dimensions.find((d) => d.id === m.dimension);
  d3.select("#metric-head").html(
    `<p class="dim">${dim.label}</p><h2>${m.label}</h2><p class="def">${m.measures}</p>`);
  renderNational();
  renderState();
  renderMeta();
}

function renderNational() {
  const m = state.metric;
  const rows = state.data.national.filter((r) => r.metric === m.id);
  const el = d3.select("#national-chart").html("");
  const note = d3.select("#national-note").text("");
  const dates = [...new Set(rows.map((r) => r.period_end))].sort().map(parseDate);
  if (dates.length === 1) {
    const r = rows[0];
    el.html(`<div class="big">${fmt(m, r.value)}</div>
      <div class="note">${r.period_label} · single snapshot, so no trend is available</div>`);
    return;
  }
  const series = d3.groups(rows, (r) => r.series);
  if (series.length > 1) {
    el.append("div").attr("class", "legend").selectAll("span").data(series).join("span")
      .style("--c", ([s]) => css(SERIES_VAR[s])).text(([s]) => SERIES_LABEL[s]);
  }
  const width = Math.max(el.node().clientWidth, 320), height = 260;
  const mg = { t: 12, r: 16, b: 28, l: 48 };
  const xd = (r) => parseDate(r.period_end);
  const span = d3.extent(dates);
  const pad = Math.max((span[1] - span[0]) * 0.04, 20 * 864e5);
  const x = d3.scaleUtc().domain([new Date(+span[0] - pad), new Date(+span[1] + pad)]).range([mg.l, width - mg.r]);
  const hi = d3.max(rows, (r) => r.value + Z * (r.se ?? 0));
  const y = d3.scaleLinear().domain([0, hi * 1.08]).nice().range([height - mg.b, mg.t]);
  const svg = el.append("svg").attr("width", width).attr("height", height).attr("role", "img")
    .attr("aria-label", `${m.label}, national, ${rows[0].period_label} to ${rows.at(-1).period_label}`);
  svg.append("g").attr("class", "grid").selectAll("line").data(y.ticks(5)).join("line")
    .attr("x1", mg.l).attr("x2", width - mg.r).attr("y1", y).attr("y2", y);
  svg.append("g").attr("transform", `translate(0,${height - mg.b})`).attr("class", "axis")
    .call(d3.axisBottom(x).ticks(Math.min(dates.length + 1, width / 80))
      .tickFormat(d3.utcFormat(span[1] - span[0] < 2 * 365 * 864e5 ? "%b %Y" : "%Y")).tickSizeOuter(0));
  svg.append("g").attr("transform", `translate(${mg.l},0)`)
    .call(d3.axisLeft(y).ticks(5).tickFormat((v) => fmt(m, v)).tickSize(0)).call((g) => g.select(".domain").remove());
  for (const [s, rs] of series) {
    const c = css(SERIES_VAR[s]);
    rs.sort((a, b) => d3.ascending(a.period_end, b.period_end));
    if (m.source_key === "htops") {
      // Waves are not confirmed comparable, so points stand alone: no connecting line or band.
      svg.append("g").selectAll("line").data(rs.filter((r) => r.se != null)).join("line")
        .attr("x1", (r) => x(xd(r))).attr("x2", (r) => x(xd(r)))
        .attr("y1", (r) => y(r.value - Z * r.se)).attr("y2", (r) => y(r.value + Z * r.se))
        .attr("stroke", c).attr("stroke-opacity", 0.4).attr("stroke-width", 2).attr("stroke-linecap", "round");
      svg.append("g").selectAll("circle").data(rs).join("circle").attr("cx", (r) => x(xd(r))).attr("cy", (r) => y(r.value))
        .attr("r", 4).attr("fill", c).attr("stroke", css("--surface")).attr("stroke-width", 2);
      continue;
    }
    svg.append("path").datum(rs).attr("fill", c).attr("opacity", 0.14)
      .attr("d", d3.area().x((r) => x(xd(r))).y0((r) => y(r.value - Z * r.se)).y1((r) => y(r.value + Z * r.se)));
    svg.append("path").datum(rs).attr("fill", "none").attr("stroke", c).attr("stroke-width", 2)
      .attr("d", d3.line().x((r) => x(xd(r))).y((r) => y(r.value)));
    svg.append("g").selectAll("circle").data(rs).join("circle").attr("cx", (r) => x(xd(r))).attr("cy", (r) => y(r.value))
      .attr("r", rs.length > 8 ? 2.5 : 4).attr("fill", c).attr("stroke", css("--surface")).attr("stroke-width", 2);
  }
  // crosshair + tooltip
  const cross = svg.append("line").attr("stroke", css("--axis")).attr("y1", mg.t).attr("y2", height - mg.b).attr("opacity", 0);
  svg.append("rect").attr("x", mg.l).attr("y", mg.t).attr("width", width - mg.l - mg.r).attr("height", height - mg.t - mg.b)
    .attr("fill", "transparent")
    .on("mousemove", (ev) => {
      const px = d3.pointer(ev)[0];
      const dt = dates.reduce((a, b) => (Math.abs(x(b) - px) < Math.abs(x(a) - px) ? b : a));
      cross.attr("x1", x(dt)).attr("x2", x(dt)).attr("opacity", 1);
      const at = rows.filter((r) => +xd(r) === +dt);
      const lines = at.map((r) =>
        `<div>${series.length > 1 ? `<span class="ts">${SERIES_LABEL[r.series]}</span><br>` : ""}<span class="tv">${fmt(m, r.value)}</span>
         <div class="ts">${fmtCI(m, r)} · n = ${r.n?.toLocaleString() ?? "n/a"}</div></div>`).join("");
      showTip(ev, `<div><strong>${at[0].period_label}</strong></div>${lines}`);
    })
    .on("mouseleave", () => { cross.attr("opacity", 0); hideTip(); });
  if (m.source_key === "htops") note.text("Waves are shown as separate points because their comparability is not confirmed (see the uncertain notes below). Bars are 95% intervals.");
  else if (m.series_note) note.text(m.series_note);
  else if (rows.some((r) => r.item_nonresponse > 0)) {
    note.text(`Item non-response (excluded from the denominator): ${rows.map((r) => `${r.wave ? `wave ${r.wave}` : r.year} ${d3.format(".1%")(r.item_nonresponse)}`).join(", ")}.`);
  }
}

function renderState() {
  const m = state.metric;
  const card = d3.select("#state-card");
  const all = state.data.state.filter((r) => r.metric === m.id);
  if (!all.length) {
    card.select(".controls").style("display", "none");
    d3.select("#state-chart").html(`<div class="empty"><span class="tag gap">gap</span>No state-level estimate. ${m.state_gap ?? ""}</div>`);
    d3.select("#state-note").text("");
    return;
  }
  card.select(".controls").style("display", null);
  const rows = all.filter((r) => r.year === state.year);
  const nat = state.data.national.find((r) => r.metric === m.id && r.year === state.year);
  const el = d3.select("#state-chart").html("");
  const ext = d3.extent(all, (r) => r.value);
  const color = d3.scaleSequential(d3.interpolateRgb(css("--seq-lo"), css("--seq-hi"))).domain(ext);
  const stateTip = (ev, r) => showTip(ev, `<div><strong>${r.state}</strong> · ${r.year}</div><div class="tv">${fmt(m, r.value)}</div>
    <div class="ts">${fmtCI(m, r)}</div><div class="ts">${r.n != null ? `n = ${r.n.toLocaleString()}` : `${r.n_counties} counties`}</div>`);

  if (state.sv === "map") {
    const width = Math.max(Math.min(el.node().clientWidth, 860), 320), height = width * 0.62;
    const states = topojson.feature(state.atlas, state.atlas.objects.states);
    const proj = d3.geoAlbersUsa().fitSize([width, height], states);
    const byFips = new Map(rows.map((r) => [r.fips, r]));
    const svg = el.append("svg").attr("width", width).attr("height", height).attr("role", "img")
      .attr("aria-label", `Map of ${m.label} by state, ${state.year}. Use the Table view for values.`);
    svg.append("g").selectAll("path").data(states.features).join("path")
      .attr("d", d3.geoPath(proj))
      .attr("fill", (f) => (byFips.has(+f.id) ? color(byFips.get(+f.id).value) : css("--nodata")))
      .attr("stroke", css("--surface")).attr("stroke-width", 1)
      .on("mousemove", (ev, f) => { const r = byFips.get(+f.id); if (r) stateTip(ev, r); })
      .on("mouseleave", hideTip);
    el.append("div").attr("class", "ramp")
      .html(`<span>${fmt(m, ext[0])}</span><i></i><span>${fmt(m, ext[1])}</span><span>· color scale fixed across all years shown</span>`);
  } else if (state.sv === "rank") {
    const sorted = [...rows].sort((a, b) => b.value - a.value);
    const width = Math.max(el.node().clientWidth, 320), row = 16;
    const mg = { t: 24, r: 16, b: 8, l: 130 };
    const height = mg.t + mg.b + row * sorted.length;
    const lo = d3.min(sorted, (r) => r.value - Z * (r.se ?? 0)), hi = d3.max(sorted, (r) => r.value + Z * (r.se ?? 0));
    const x = d3.scaleLinear().domain([lo, hi]).nice().range([mg.l, width - mg.r]);
    const y = (i) => mg.t + row * i + row / 2;
    const svg = el.append("svg").attr("width", width).attr("height", height).attr("role", "img")
      .attr("aria-label", `States ranked by ${m.label}, ${state.year}, with 95% intervals`);
    svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(6)).join("line")
      .attr("x1", x).attr("x2", x).attr("y1", mg.t).attr("y2", height - mg.b);
    svg.append("g").attr("transform", `translate(0,${mg.t})`)
      .call(d3.axisTop(x).ticks(6).tickFormat((v) => fmt(m, v)).tickSize(0)).call((g) => g.select(".domain").remove());
    if (nat) {
      svg.append("line").attr("x1", x(nat.value)).attr("x2", x(nat.value)).attr("y1", mg.t).attr("y2", height - mg.b)
        .attr("stroke", css("--ink-2")).attr("stroke-dasharray", "3 3");
    }
    const g = svg.append("g").selectAll("g").data(sorted).join("g").attr("transform", (_, i) => `translate(0,${y(i)})`);
    g.append("text").attr("x", mg.l - 8).attr("dy", "0.32em").attr("text-anchor", "end").style("fill", css("--ink-2")).text((r) => r.state);
    g.filter((r) => r.se != null).append("line").attr("x1", (r) => x(r.value - Z * r.se)).attr("x2", (r) => x(r.value + Z * r.se))
      .attr("stroke", css("--series-1")).attr("stroke-opacity", 0.35).attr("stroke-width", 2).attr("stroke-linecap", "round");
    g.append("circle").attr("cx", (r) => x(r.value)).attr("r", 4).attr("fill", css("--series-1"))
      .attr("stroke", css("--surface")).attr("stroke-width", 2);
    g.append("rect").attr("x", 0).attr("y", -row / 2).attr("width", width).attr("height", row).attr("fill", "transparent")
      .on("mousemove", stateTip).on("mouseleave", hideTip);
  } else {
    const sorted = [...rows].sort((a, b) => d3.ascending(a.state, b.state));
    const countCol = sorted[0].n != null ? "n" : "Counties";
    el.html(`<table><thead><tr><th>State</th><th class="num">Estimate</th><th class="num">95% CI low</th><th class="num">95% CI high</th><th class="num">${countCol}</th></tr></thead><tbody>${
      sorted.map((r) => `<tr><td>${r.state}</td><td class="num">${fmt(m, r.value)}</td>
        <td class="num">${r.se == null ? "" : fmt(m, r.value - Z * r.se)}</td><td class="num">${r.se == null ? "" : fmt(m, r.value + Z * r.se)}</td>
        <td class="num">${(r.n ?? r.n_counties).toLocaleString()}</td></tr>`).join("")}</tbody></table>`);
  }
  const overlapping = rows.length ? stateOverlapShare(rows) : 0;
  d3.select("#state-note").text(
    `${state.sv === "rank" && nat ? "Dashed line = national estimate. " : ""}` +
    `In ${d3.format(".0%")(overlapping)} of state pairs the 95% intervals overlap. Overlap is a rough check, not a significance test, ` +
    `but where it is common, small differences in rank should not be read as real differences.`);
}

function stateOverlapShare(rows) {
  const rs = rows.filter((r) => r.se != null);
  let o = 0, n = 0;
  for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
    n++;
    if (Math.abs(rs[i].value - rs[j].value) < Z * (rs[i].se + rs[j].se)) o++;
  }
  return n ? o / n : 0;
}

function renderMeta() {
  const m = state.metric;
  const field = (k, v) => (v ? `<dt>${k}</dt><dd>${v}</dd>` : "");
  d3.select("#meta-card").html(`<h3>What this figure is</h3><dl class="meta">
    ${field("Measures", m.measures)}
    ${field("Does not measure", m.does_not_measure)}
    ${field("Question wording", m.wording)}
    ${field("Counted as yes", m.response_cut)}
    ${field("Universe", m.universe)}
    ${field("Years", m.years.join(", "))}
    ${field("Geography", m.geography.join(", "))}
    ${field("Weight", m.weight)}
    ${field("Standard errors", m.se_method)}
    ${field("Source", `<a href="${m.source_url}" target="_blank" rel="noopener">${m.source}</a>`)}
    ${field("Comparability", m.years_note)}
  </dl>${m.tags.length ? `<div class="tags">${tagsHTML(m.tags)}</div>` : ""}`);
}

// ---------- this week ----------
function renderWeek() {
  const { refresh, dimensions, metrics, gaps } = state.data;
  const asOf = refresh.date;
  const changes = refresh.new_data;
  const last = refresh.last_new_data;
  d3.select("#week-status").html(`
    <h2>Refreshed ${fmtDate(parseDate(asOf))}</h2>
    <p>${changes.length
      ? `<strong>New data this week:</strong> ${changes.map((c) => c.label.toLowerCase()).join("; ")}.`
      : `No new data was released since the last refresh${last && last.date !== asOf ? ` (last new data arrived ${fmtDate(parseDate(last.date))})` : ""}. The figures below are the newest available, and each one shows its age.`}</p>
    <p class="note"><span class="tag gap">gap</span>No source here measures cohesion weekly. The freshest (Census HTOPS) arrives about every two months, and most others every two years. This page is checked and rebuilt weekly.</p>`);

  const grid = d3.select("#week-grid").html("");
  for (const dim of dimensions) {
    const ms = metrics.filter((m) => m.dimension === dim.id);
    const card = grid.append("div").attr("class", "card");
    card.append("div").attr("class", "dimhead").html(`<h3>${dim.label}</h3><span>${dim.short}</span>`);
    if (!ms.length) {
      const g = gaps.find((x) => x.dimension === dim.id);
      card.append("p").attr("class", "plain").html(`<span class="tag gap">gap</span>${g ? g.text : "No measure yet."}`);
      continue;
    }
    const head = ms.find((m) => m.headline) ?? ms[0];
    const r = latestRow(head.id);
    card.append("div").attr("class", "big").text(fmt(head, r.value));
    card.append("p").attr("class", "plain").text(head.plain);
    card.append("span").attr("class", `age ${isFresh(r.period_end, asOf) ? "fresh" : "stale"}`)
      .text(`${r.period_label} · ${ageText(r.period_end, asOf)}`);
    const prev = state.data.national.filter((x) => x.metric === head.id && x.series === r.series && x.period_end < r.period_end);
    if (prev.length) {
      const p = d3.greatest(prev, (x) => x.period_end);
      card.append("div").attr("class", "prev")
        .html(`Previous reading: ${fmt(head, p.value)} (${p.period_label}).${head.tags.some((t) => /differ between waves|mode/.test(t.text)) || head.series_note ? ' <span class="tag uncertain">uncertain</span>comparability, see details.' : ""}`);
    }
    const others = ms.filter((m) => m !== head);
    if (others.length) {
      card.append("ul").attr("class", "others").selectAll("li").data(others).join("li")
        .html((m) => { const o = latestRow(m.id); return `<span>${m.label}</span><b title="${o.period_label}">${fmt(m, o.value)} · ${o.period_end.slice(0, 4)}</b>`; });
    }
    card.append("button").attr("class", "linkish")
      .text(head.geography.includes("state") ? "Details, sources and states →" : "Details and sources →")
      .on("click", () => { showView("explore"); selectMetric(head.id); window.scrollTo(0, 0); });
  }

  const f = refresh.freshness;
  d3.select("#week-sources").html(!f ? "" : `<h3>Source check, ${fmtDate(parseDate(f.checked))}</h3>
    <table><thead><tr><th>Source</th><th>Newest data used</th><th>Release cadence</th><th>Newer release upstream?</th></tr></thead><tbody>${
      Object.values(f.sources).map((s) => `<tr><td>${s.label}</td><td>${s.collected ?? s.release_used}</td><td>${s.cadence}</td>
        <td>${!s.reachable ? "Could not check" : s.update_available ? "Yes, needs review before it is added" : "No"}</td></tr>`).join("")}</tbody></table>`);
}

// ---------- sources & limits ----------
function renderSources() {
  const { metrics, gaps, dimensions } = state.data;
  const bySource = d3.groups(metrics, (m) => m.source);
  const dimLabel = (id) => dimensions.find((d) => d.id === id)?.label ?? "General";
  d3.select("#sources").html(`
    <div class="card"><h2>Definition</h2>
      <p>Here social cohesion means the strength of the relationships, expectations and participation that hold people together across a society. It is broken into dimensions that are measured and shown separately:</p>
      <ul>${dimensions.map((d) => `<li><strong>${d.label}</strong>: ${d.definition}</li>`).join("")}</ul>
      <p>This is a working definition. Its descriptive use (what the data show) is kept apart from any normative claim (how much cohesion a society should have, or which kind). This app makes descriptive claims only.</p>
    </div>
    <div class="card"><h2>Known gaps</h2>
      <div class="tags">${gaps.map((g) => `<div class="tagline"><span class="tag gap">gap</span><strong>${dimLabel(g.dimension)}.</strong> ${g.text}</div>`).join("")}</div>
    </div>
    ${bySource.map(([src, ms]) => `<div class="card"><h2>${src}</h2>
      <p><a href="${ms[0].source_url}" target="_blank" rel="noopener">${ms[0].source_url}</a></p>
      <dl class="meta">
        <dt>Universe</dt><dd>${ms[0].universe}</dd>
        <dt>Years used</dt><dd>${[...new Set(ms.flatMap((m) => m.years))].sort().join(", ")}</dd>
        <dt>Geography</dt><dd>${ms[0].geography.join(", ")}</dd>
        <dt>Weight</dt><dd>${ms[0].weight}</dd>
        <dt>Standard errors</dt><dd>${ms[0].se_method}</dd>
        <dt>Metrics</dt><dd>${ms.map((m) => m.label).join("; ")}</dd>
      </dl>
      ${ms[0].series_note ? `<p class="note">${ms[0].series_note}</p>` : ""}
      <div class="tags">${tagsHTML([...new Map(ms.flatMap((m) => m.tags).map((t) => [t.text, t])).values()])}</div>
    </div>`).join("")}
  `);
}

// ---------- CSV ----------
function downloadCSV() {
  const m = state.metric;
  const rows = state.data.state.filter((r) => r.metric === m.id);
  const head = [`# ${m.label}`, `# Source: ${m.source} (${m.source_url})`, `# Counted as yes: ${m.response_cut}`,
    `# Weight: ${m.weight}; SE: ${m.se_method}`];
  const cols = ["year", "fips", "abbr", "state", "value", "se", "ci95_low", "ci95_high", rows[0]?.n != null ? "n" : "n_counties"];
  const body = rows.map((r) => [r.year, r.fips, r.abbr, `"${r.state}"`, r.value, r.se ?? "",
    r.se == null ? "" : r.value - Z * r.se, r.se == null ? "" : r.value + Z * r.se, r.n ?? r.n_counties].join(","));
  const blob = new Blob([[...head, cols.join(","), ...body].join("\n")], { type: "text/csv" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `${m.id}_by_state.csv` });
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---------- boot ----------
async function main() {
  const [data, atlas] = await Promise.all([d3.json("data/cohesion.json"), d3.json(ATLAS_URL)]);
  Object.assign(state, { data, atlas });
  d3.select("#built").text(data.generated);
  renderNav();
  renderSources();
  d3.selectAll(".tabs button").on("click", function () { showView(this.dataset.view); });
  renderWeek();
  d3.selectAll(".seg button").on("click", function () {
    state.sv = this.dataset.sv;
    d3.selectAll(".seg button").attr("aria-pressed", function () { return this.dataset.sv === state.sv; });
    renderState();
  });
  d3.select("#year-select").on("change", function () { state.year = +this.value; renderState(); });
  d3.select("#csv-btn").on("click", downloadCSV);
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderMetric, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderMetric);
  const fromHash = () => {
    const h = location.hash.slice(1);
    return data.metrics.some((m) => m.id === h) ? h : null;
  };
  window.addEventListener("hashchange", () => {
    if (fromHash() && fromHash() !== state.metric?.id) { showView("explore"); selectMetric(fromHash()); }
  });
  const initial = fromHash();
  selectMetric(initial ?? "htops_support");
  showView(initial ? "explore" : "week");
}

main().catch((e) => {
  document.querySelector("#metric-panel").innerHTML =
    `<div class="card">Could not load data: ${e.message}. Serve this folder over HTTP (see README) instead of opening the file directly.</div>`;
});
