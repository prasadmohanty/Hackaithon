// Class-level summary dashboard (GET /api/reports/class).
import { api } from "../api.js";
import { barChart, donut } from "../charts.js";
import { store } from "../store.js";
import { $, esc, a11yChips, avatar, bandBadge, downloadJSON, empty, html, pct, scoreBar, scoreColor, trendLabel } from "../ui.js";

export async function render(root) {
  const [report] = await Promise.all([api.classReport(), store.ensure({ settings: true })]);
  const t = report.totals;
  const { weak, mastery } = report.thresholds;
  const color = (v) => scoreColor(v, weak, mastery);

  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Class dashboard</h1>
        <p>Class-level summary of strengths, learning gaps, trends and accessibility needs.</p></div>
      <div class="row">
        <a class="btn" href="#/assessments">＋ Record assessment</a>
        <button class="btn" id="dl">⤓ Export JSON</button>
      </div>
    </div>

    <div class="grid grid-4">
      ${kpi("Learners", t.students, `${t.with_accessibility_needs} with accessibility needs`, "var(--primary-soft)")}
      ${kpi("Class average", t.class_average === null ? "—" : t.class_average.toFixed(1), `${t.assessments} assessments analysed`, "var(--info-soft)", "%")}
      ${kpi("Needs support", report.students_needing_support.length,
            `${t.on_track} on track · ${t.excelling} excelling`, "var(--warn-soft)")}
      ${kpi("Data issues", t.data_issues, "rejected records in log", "var(--danger-soft)")}
    </div>

    <div class="grid grid-main" style="margin-top:18px">
      <div class="card">
        <div class="card-head"><div><div class="section-title">Topic performance (class average)</div>
          <p>Weighted averages across all learners, weakest first. Dashed lines = weak (${weak}%) and mastery (${mastery}%) thresholds.</p></div></div>
        ${barChart(report.topics.map((x) => ({ label: x.topic_name, value: x.class_average,
            tip: `<b>${esc(x.topic_name)}</b> (${esc(x.subject_name)})<br>Average ${x.class_average}% · ${x.students_assessed} learners<br>${x.weak_count} weak · ${x.at_risk_count} at risk · ${x.mastered_count} mastered` })),
          { colorFn: color, thresholds: [{ value: weak, label: "weak", color: "var(--danger)" }, { value: mastery, label: "mastery", color: "var(--success)" }] })}
      </div>
      <div class="stack">
        <div class="card">
          <div class="section-title" style="margin-bottom:12px">Learner bands</div>
          ${donut([
            { label: "Needs support", value: t.needs_support, color: "var(--danger)" },
            { label: "On track", value: t.on_track, color: "var(--info)" },
            { label: "Excelling", value: t.excelling, color: "var(--success)" },
          ], { centerValue: t.students, centerLabel: "learners" })}
        </div>
        <div class="card">
          <div class="section-title" style="margin-bottom:8px">Score distribution</div>
          ${report.score_distribution.map((d) => {
            const max = Math.max(1, ...report.score_distribution.map((x) => x.count));
            return html`<div class="dist-row"><span class="l">${d.range}</span>
              <div class="bar"><span style="width:${(d.count / max) * 100}%;background:var(--primary)"></span></div><span class="c">${d.count}</span></div>`;
          })}
        </div>
      </div>
    </div>

    <div class="grid grid-3" style="margin-top:18px">
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">Most common learning gaps</div>
        ${report.common_weak_topics.length ? report.common_weak_topics.map((x) => html`
          <div class="topic-pill"><div><div class="t">${x.topic_name}</div>
            <div class="s">${x.subject_name} · ${x.students_weak.join(", ")}</div></div>
            <div style="text-align:right"><span class="badge st-weak">${x.weak_count} weak</span>
            ${x.at_risk_count ? html`<div style="margin-top:4px"><span class="badge st-at_risk">${x.at_risk_count} at risk</span></div>` : ""}</div></div>`)
          : empty("No common gaps 🎉", "✓")}
      </div>
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">Trends</div>
        <div class="subtle" style="margin-bottom:6px">Top improvers</div>
        ${report.top_improvers.length ? report.top_improvers.map((s) => personRow(s)) : html`<p class="subtle">None yet</p>`}
        <div class="subtle" style="margin:14px 0 6px">Declining — check in</div>
        ${report.declining_students.length ? report.declining_students.map((s) => personRow(s)) : html`<p class="subtle">No declining learners</p>`}
      </div>
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">Subjects & accessibility</div>
        ${report.subjects.map((s) => html`<div style="margin-bottom:12px"><div class="row" style="justify-content:space-between">
            <b>${s.subject_name}</b><span class="subtle">${s.students_assessed} learners</span></div>${scoreBar(s.class_average, weak, mastery)}</div>`)}
        <div class="subtle" style="margin:16px 0 8px">Declared accessibility needs</div>
        <div class="row">${Object.entries(report.accessibility_needs).map(([k, v]) => html`<span class="chip a11y">♿ ${k} · ${v}</span>`)}</div>
      </div>
    </div>

    <div class="card flush" style="margin-top:18px">
      <div class="card-head"><div><div class="section-title">All learners <span class="count">${report.students.length}</span></div>
        <p>Click a learner to open their individual progress report.</p></div></div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>Learner</th><th style="min-width:180px">Overall</th><th>Trend</th><th>Weak / at-risk topics</th><th>Strengths</th><th>Accessibility</th><th>Band</th></tr></thead>
        <tbody>${report.students.map((s) => html`
          <tr class="clickable" data-href="#/student/${s.id}" tabindex="0">
            <td><div class="person">${avatar(s.name)}<div><div class="n">${s.name}</div>
              <div class="subtle">${s.assessment_count} assessments${s.data_issues ? html` · <span style="color:var(--danger)">⚑ ${s.data_issues} issues</span>` : ""}</div></div></div></td>
            <td>${scoreBar(s.overall_average, weak, mastery)}</td>
            <td>${trendLabel(s.trend, s.slope)}</td>
            <td><div class="row" style="gap:5px">${s.weak_topics.length ? s.weak_topics.map((w) => html`<span class="chip">${w}</span>`) : html`<span class="subtle">—</span>`}</div></td>
            <td class="num">${s.strengths.length}</td>
            <td><div class="row" style="gap:5px">${s.accessibility_needs.length ? a11yChips(s.accessibility_needs) : html`<span class="subtle">—</span>`}</div></td>
            <td>${bandBadge(s.band)}</td>
          </tr>`)}</tbody></table></div>
    </div>`;

  root.querySelectorAll("tr[data-href]").forEach((tr) => {
    const go = () => (location.hash = tr.dataset.href);
    tr.addEventListener("click", go);
    tr.addEventListener("keydown", (e) => e.key === "Enter" && go());
  });
  $("#dl", root).addEventListener("click", () => downloadJSON("learn4all-class-summary.json", report));
  return "Class dashboard";
}

function kpi(label, value, foot, tint, unit = "") {
  return html`<div class="card kpi" style="--kpi-tint:${tint}"><div class="label">${label}</div>
    <div class="value">${value}${unit ? html`<small>${unit}</small>` : ""}</div><div class="foot">${foot}</div></div>`;
}

function personRow(s) {
  return html`<a class="topic-pill" href="#/student/${s.id}" style="color:inherit;text-decoration:none">
    <div class="person">${avatar(s.name)}<div><div class="t">${s.name}</div><div class="s">${pct(s.overall_average)} overall</div></div></div>
    ${trendLabel(s.trend, s.slope)}</a>`;
}
