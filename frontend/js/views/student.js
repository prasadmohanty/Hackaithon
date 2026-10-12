// Individual learner progress report (GET /api/students/{id}/report).
import { api } from "../api.js";
import { bindTips, lineChart, PALETTE, sparkline } from "../charts.js";
import { assessmentDialog, studentDialog } from "../forms.js";
import {
  $, $$, a11yChips, avatar, bandBadge, catChip, confirmDialog, downloadJSON, empty, esc, fmtDate, html,
  label, num, pct, priorityBadge, scoreBar, statusBadge, title, toast, trendLabel,
} from "../ui.js";

export async function render(root, [id]) {
  const r = await api.report(id);
  const s = r.student, sum = r.summary, perf = r.performance, plan = r.study_plan;
  const weak = r.settings_used.weak_threshold, mastery = r.settings_used.mastery_threshold;
  const budgetPct = plan.weekly_budget_minutes ? Math.min(100, (plan.total_minutes / plan.weekly_budget_minutes) * 100) : 100;

  root.innerHTML = html`
    <div class="row" style="margin-bottom:14px"><a href="#/students" class="subtle">← All learners</a></div>

    <section class="card hero">
      ${avatar(s.name)}
      <div>
        <h1>${s.name}</h1>
        <div class="meta">${s.grade_level || "No grade"} · ${s.email || "no email"} · ${s.weekly_study_minutes} min/week study time</div>
        <div class="row" style="margin-top:10px;gap:6px">
          ${s.accessibility_needs.length ? s.accessibility_needs.map((n) => html`<span class="chip">♿ ${n}</span>`) : html`<span class="chip">No accessibility needs declared</span>`}
          ${s.preferred_categories.map((c) => html`<span class="chip">♥ prefers ${c}</span>`)}
        </div>
      </div>
      <div class="hero-stats">
        <div class="hero-stat"><div class="v">${pct(sum.overall_average)}</div><div class="l">Overall (weighted)</div></div>
        <div class="hero-stat"><div class="v">${sum.assessment_count}</div><div class="l">Assessments</div></div>
        <div class="hero-stat"><div class="v">${sum.gap_count}</div><div class="l">Learning gaps</div></div>
        <div class="hero-stat"><div class="v">${sum.strength_count}</div><div class="l">Strengths</div></div>
      </div>
    </section>

    <div class="row" style="margin:16px 0 18px">
      ${bandBadge(sum.band)} ${trendLabel(sum.overall_trend, sum.overall_slope)}
      <span class="subtle">${sum.period.from ? `${fmtDate(sum.period.from)} → ${fmtDate(sum.period.to)}` : "No assessment history"}</span>
      <span class="spacer"></span>
      <button class="btn" id="add-a">＋ Assessment</button>
      <button class="btn" id="edit">✎ Edit learner</button>
      <button class="btn" id="dl">⤓ JSON</button>
      <button class="btn" onclick="window.print()">⎙ Print</button>
    </div>

    ${r.data_issues.length ? html`<div class="callout danger" style="margin-bottom:18px">
      <b>⚑ ${r.data_issues.length} assessment record(s) for this learner were rejected</b> — incomplete, invalid, duplicate or inconsistent.
      They are excluded from all calculations. <a href="#issues">Review below</a>.</div>` : ""}

    <div class="grid grid-main">
      <div class="card">
        <div class="card-head"><div><div class="section-title">Progress over time</div><p>Percentage scores per assessment date.</p></div>
          <div class="tabs" style="margin:0" role="tablist">
            <button class="active" data-mode="overall">Overall</button><button data-mode="topics">By topic</button><button data-mode="gaps">Gaps only</button></div></div>
        <div id="chart"></div>
      </div>
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">Next actions</div>
        ${r.next_actions.length ? html`<ul class="actions-list">${r.next_actions.map((a) => html`<li>${priorityBadge(a.priority)}<span>${a.action}</span></li>`)}</ul>`
          : empty("Nothing to do — great work!", "✓")}
      </div>
    </div>

    <div class="grid grid-3" style="margin-top:18px">
      ${perf.subjects.map((x) => html`<div class="card">
        <div class="row" style="justify-content:space-between"><b>${x.subject_name}</b>${trendLabel(x.trend, x.slope)}</div>
        <div style="margin:10px 0 6px">${scoreBar(x.average, weak, mastery)}</div>
        <div class="subtle">${x.topic_count} topics · ${x.assessment_count} assessments · ${x.weak_count} gap(s)</div></div>`)}
    </div>

    <div class="grid grid-2" style="margin-top:18px">
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">💪 Strengths <span class="count">${perf.strengths.length}</span></div>
        ${perf.strengths.length ? perf.strengths.map((t) => html`<div class="topic-pill"><div><div class="t">${t.topic_name}</div>
          <div class="s">${t.subject_name} · ${t.count} results · latest ${pct(t.latest, 0)}</div></div>
          <div class="row">${statusBadge(t.status)}<b>${pct(t.weighted_average)}</b></div></div>`) : empty("No strengths identified yet")}
      </div>
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">🎯 Weak topics (prioritised) <span class="count">${perf.weak_topics.length}</span></div>
        ${perf.weak_topics.length ? perf.weak_topics.map((t) => html`<div class="topic-pill" title="${t.explanation}"><div><div class="t">${t.topic_name}</div>
          <div class="s">${t.explanation}</div></div>
          <div style="text-align:right">${statusBadge(t.status)}<div class="subtle" style="margin-top:4px">priority ${t.priority} · ${t.priority_label}</div></div></div>`)
          : empty("No learning gaps — every assessed topic is above threshold.", "✓")}
      </div>
    </div>

    <div class="card flush" style="margin-top:18px">
      <div class="card-head"><div><div class="section-title">Topic-wise performance</div>
        <p>Weighted average uses assessment-type weights and recency. Markers on bars show weak (${weak}%) and mastery (${mastery}%) thresholds.</p></div></div>
      <div class="table-wrap"><table class="table">
        <thead><tr><th>Topic</th><th class="num">#</th><th class="num">Average</th><th style="min-width:170px">Weighted avg</th><th class="num">Latest</th><th class="num">Change</th><th>History</th><th>Trend</th><th>Status</th></tr></thead>
        <tbody>${perf.topics.map((t) => html`<tr title="${t.explanation}">
          <td><b>${t.topic_name}</b><div class="subtle">${t.subject_name}</div></td>
          <td class="num">${t.count}</td>
          <td class="num">${pct(t.average)}</td>
          <td>${scoreBar(t.weighted_average, weak, mastery)}</td>
          <td class="num">${pct(t.latest, 0)}</td>
          <td class="num">${t.change === null ? "—" : html`<span class="trend ${t.change >= 0 ? "improving" : "declining"}">${t.change > 0 ? "+" : ""}${num(t.change)}</span>`}
            ${t.improvement_rate !== null ? html`<div class="subtle">${t.improvement_rate > 0 ? "+" : ""}${t.improvement_rate}%</div>` : ""}</td>
          <td>${sparkline(t.history.map((h) => h.percentage), { color: t.trend === "declining" ? "var(--danger)" : "var(--primary)" })}</td>
          <td>${trendLabel(t.trend, t.slope)}</td>
          <td>${statusBadge(t.status)}</td></tr>`)}</tbody></table></div>
      ${perf.topics.length ? "" : empty("No valid assessments yet. Record one to generate the report.")}
    </div>

    <div class="card" style="margin-top:18px">
      <div class="card-head"><div><div class="section-title">📚 Personalised study plan</div>
        <p>Accessibility-aware, rule-based recommendations. Every item explains why it was chosen.</p></div>
        <div style="min-width:220px"><div class="row" style="justify-content:space-between"><span class="subtle">Weekly time budget</span>
          <b>${plan.total_minutes} / ${plan.weekly_budget_minutes} min</b></div>
          <div class="bar" style="margin-top:6px"><span style="width:${budgetPct}%;background:${plan.total_minutes > plan.weekly_budget_minutes ? "var(--warn)" : "var(--success)"}"></span></div></div>
      </div>
      ${plan.recommendations.length ? html`<div class="stack" style="gap:12px">${plan.recommendations.map(recCard)}</div>`
        : empty(perf.weak_topics.length ? "No eligible resources for the current gaps." : "No gaps — no remedial resources needed.", "📚")}
      ${plan.uncovered_gaps.length ? html`<div class="callout warn" style="margin-top:14px"><b>Gaps without a suitable resource:</b>
        ${plan.uncovered_gaps.map((g) => html`<div>• ${g.topic_name} (${label(g.status)}) — ${g.reason}</div>`)}</div>` : ""}
      ${plan.excluded.length ? html`<details style="margin-top:16px"><summary class="section-title" style="cursor:pointer">
          Filtered out <span class="count">${plan.excluded.length} resources</span> — why they were not recommended</summary>
        <div class="grid grid-2" style="margin-top:12px;gap:10px">${plan.excluded.map((e) => html`<div class="excluded">
          <b>${e.resource.title}</b><span class="subtle">${e.topic_name} · ${e.resource.category} · ${e.resource.difficulty}</span>
          <div>${e.reasons.join(" · ")}</div></div>`)}</div></details>` : ""}
    </div>

    ${r.data_issues.length ? html`<div class="card flush" style="margin-top:18px" id="issues">
      <div class="card-head"><div><div class="section-title">⚑ Data-quality issues <span class="count">${r.data_issues.length}</span></div>
        <p>Rejected records — not used in any calculation.</p></div><a class="btn sm" href="#/quality">Open log</a></div>
      <div class="table-wrap"><table class="table"><thead><tr><th>Submitted data</th><th>Problems found</th><th>Source</th></tr></thead>
        <tbody>${r.data_issues.map((i) => html`<tr><td class="mono">${payloadSummary(i.payload)}</td>
          <td>${i.errors.map((e) => html`<div><b>${e.field}</b>: ${e.message}</div>`)}</td><td>${i.source}</td></tr>`)}</tbody></table></div></div>` : ""}

    <div class="card flush" style="margin-top:18px">
      <div class="card-head"><div><div class="section-title">Assessment history</div><p>All valid records, newest first.</p></div></div>
      <div id="history"></div>
    </div>

    <div class="callout" style="margin-top:18px">ⓘ <b>How was this decided?</b> Topic statuses use thresholds (weak &lt; ${weak}%, mastery ≥ ${mastery}%)
      and require ${r.settings_used.min_evidence}+ results to confirm a gap. Recommendations pass rules R1–R6.
      <a href="#/rules">See all rules and formulas →</a></div>`;

  // --- chart modes ---
  const drawChart = (mode) => {
    const thresholds = [{ value: weak, label: `weak ${weak}%`, color: "var(--danger)" }, { value: mastery, label: `mastery ${mastery}%`, color: "var(--success)" }];
    let series;
    if (mode === "overall") series = [{ name: "Average score", color: PALETTE[0], points: perf.timeline.map((p) => ({ date: p.date, value: p.average, note: `${p.count} assessment(s)` })) }];
    else {
      const list = mode === "gaps" ? perf.topics.filter((t) => ["weak", "at_risk", "developing"].includes(t.status)) : perf.topics;
      series = list.map((t, i) => ({ name: t.topic_name, color: PALETTE[i % PALETTE.length], points: t.history.map((h) => ({ date: h.date, value: h.percentage, note: h.assessment_type })) }));
    }
    $("#chart", root).innerHTML = series.length ? lineChart(series, { thresholds }) : empty("No gap topics to plot");
    bindTips($("#chart", root));
  };
  $$("[data-mode]", root).forEach((b) => b.addEventListener("click", () => {
    $$("[data-mode]", root).forEach((x) => x.classList.toggle("active", x === b));
    drawChart(b.dataset.mode);
  }));
  drawChart("overall");

  // --- history table ---
  const loadHistory = async () => {
    const { items } = await api.assessments({ student_id: s.id });
    const box = $("#history", root);
    box.innerHTML = items.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th>Date</th><th>Subject</th><th>Topic</th><th>Type</th><th class="num">Score</th><th class="num">%</th><th>Notes</th><th></th></tr></thead>
      <tbody>${[...items].reverse().map((a) => html`<tr><td class="nowrap">${fmtDate(a.date)}</td><td>${a.subject_name}</td><td>${a.topic_name}</td>
        <td>${title(a.assessment_type)}</td><td class="num">${num(a.score, 0)} / ${num(a.max_score, 0)}</td><td class="num"><b>${pct(a.percentage)}</b></td>
        <td class="subtle">${a.notes}</td>
        <td class="nowrap"><button class="btn sm ghost" data-ea="${a.id}" aria-label="Edit">✎</button><button class="btn sm ghost danger" data-da="${a.id}" aria-label="Delete">🗑</button></td></tr>`)}
      </tbody></table></div>` : empty("No assessments recorded");
    $$("[data-ea]", box).forEach((b) => b.addEventListener("click", () =>
      assessmentDialog({ existing: items.find((a) => a.id === +b.dataset.ea), onSaved: () => render(root, [id]) })));
    $$("[data-da]", box).forEach((b) => b.addEventListener("click", async () => {
      if (!(await confirmDialog("Delete this assessment? The report will be recalculated."))) return;
      await api.deleteAssessment(+b.dataset.da);
      toast("Assessment deleted", "success");
      render(root, [id]);
    }));
  };
  await loadHistory();

  $("#add-a", root).addEventListener("click", () => assessmentDialog({ studentId: s.id, onSaved: () => render(root, [id]) }));
  $("#edit", root).addEventListener("click", () => studentDialog(s, () => render(root, [id])));
  $("#dl", root).addEventListener("click", () => downloadJSON(`learn4all-report-${s.name.replace(/\s+/g, "-").toLowerCase()}.json`, r));
  bindTips(root);
  return s.name;
}

function recCard(rec) {
  const res = rec.resource;
  return html`<article class="rec">
    <div class="rec-rank">${rec.rank}</div>
    <div class="rec-body">
      <div class="rec-title">${res.url ? html`<a href="${res.url}" target="_blank" rel="noopener">${res.title} ↗</a>` : res.title}</div>
      <div class="rec-meta">${catChip(res.category)}<span class="chip">${res.difficulty}</span><span class="chip">⏱ ${res.estimated_minutes} min</span>
        <span class="chip">${rec.subject_name} · ${rec.topic_name}</span>${statusBadge(rec.gap_status)}
        ${a11yChips(res.formats)}
        ${rec.within_weekly_budget ? "" : html`<span class="chip" style="color:var(--warn)">beyond weekly budget</span>`}</div>
      <div class="muted" style="font-size:13.5px">${rec.summary}</div>
      <ul class="reasons">${rec.reasons.map((x) => html`<li>${x}</li>`)}</ul>
      <details class="trace"><summary>Full rule trace</summary><table>
        ${rec.rule_trace.map((o) => html`<tr><td class="mono">${o.rule}</td><td>${o.allowed ? "✓" : "✕"}</td>
          <td class="mono">${o.points >= 0 ? "+" : ""}${o.points}</td><td>${o.reason}</td></tr>`)}</table></details>
    </div>
    <div class="rec-score"><div class="v">${num(rec.score)}</div><div class="l">score</div>${priorityBadge(rec.priority_label)}</div>
  </article>`;
}

function payloadSummary(p) {
  return Object.entries(p).filter(([k]) => k !== "notes").map(([k, v]) => `${k}=${v === "" ? "∅" : v}`).join(", ") + (p.notes ? ` — “${p.notes}”` : "");
}
