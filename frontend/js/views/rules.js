// Explains every rule, formula and threshold used by the backend (GET /api/rules).
import { api } from "../api.js";
import { html, statusBadge } from "../ui.js";

export async function render(root) {
  const r = await api.rules();
  root.innerHTML = html`
    <div class="page-head"><div><h1>Rules explained</h1>
      <p>Learn4All is fully explainable: these are the exact rules the API applies, using the current settings.</p></div>
      <a class="btn" href="#/settings">⚙ Adjust thresholds</a></div>

    <div class="grid grid-2">
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">1 · Topic status rules</div>
        <ol style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:8px">${r.status_rules.map((x) => html`<li>${x}</li>`)}</ol>
        <div class="row" style="margin-top:16px;gap:6px">${r.status_definitions.map((s) => html`<span title="${s.description}">${statusBadge(s.code)}</span>`)}</div>
      </div>
      <div class="card">
        <div class="section-title" style="margin-bottom:12px">2 · Formulas</div>
        <dl class="kv">${Object.entries(r.formulas).map(([k, v]) => html`<dt>${k.replace(/_/g, " ")}</dt><dd><code>${v}</code></dd>`)}</dl>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <div class="section-title" style="margin-bottom:6px">3 · Recommendation rules</div>
      <p class="subtle" style="margin-top:0">Filter rules can exclude a resource; scoring rules add points. Score = gap priority ÷ 10 + rule points.</p>
      <div class="grid grid-3">${r.recommendation_rules.map((x) => html`<div class="topic-pill" style="flex-direction:column;align-items:flex-start;margin:0">
        <div class="row"><span class="method ${x.kind === "filter" ? "m-DELETE" : "m-GET"}">${x.code}</span><b>${x.title}</b><span class="chip">${x.kind}</span></div>
        <div class="muted" style="font-size:13px">${x.description}</div></div>`)}</div>
    </div>

    <div class="grid grid-2" style="margin-top:18px">
      <div class="card"><div class="section-title" style="margin-bottom:12px">4 · Plan selection</div>
        <ul style="margin:0;padding-left:20px">${r.selection_policy.map((x) => html`<li style="margin-bottom:6px">${x}</li>`)}</ul></div>
      <div class="card"><div class="section-title" style="margin-bottom:12px">Current settings</div>
        <dl class="kv">${Object.entries(r.settings).map(([k, v]) => html`<dt>${k}</dt><dd><b>${v}</b></dd>`)}</dl></div>
    </div>`;
  return "Rules explained";
}
