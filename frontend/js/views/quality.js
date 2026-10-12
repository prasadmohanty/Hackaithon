// Data-quality log: every rejected record with the validation errors found.
import { api } from "../api.js";
import { $, $$, confirmDialog, empty, fmtDate, html, toast } from "../ui.js";
import { refreshIssueBadge } from "../app.js";

export async function render(root) {
  const { items } = await api.validationLog();
  const byField = {};
  items.forEach((i) => i.errors.forEach((e) => (byField[e.field] = (byField[e.field] || 0) + 1)));

  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Data quality</h1><p>Records rejected because they were missing, invalid, duplicate or inconsistent. They never affect analytics.</p></div>
      ${items.length ? html`<button class="btn danger" id="clear">Clear log</button>` : ""}
    </div>
    <div class="grid grid-4" style="margin-bottom:18px">
      <div class="card kpi" style="--kpi-tint:var(--danger-soft)"><div class="label">Rejected records</div><div class="value">${items.length}</div></div>
      ${Object.entries(byField).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([f, c]) => html`<div class="card kpi">
        <div class="label">Problems in “${f}”</div><div class="value">${c}</div></div>`)}
    </div>
    <div class="card flush">${items.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th>When</th><th>Learner</th><th>Source</th><th>Submitted data</th><th>Problems</th><th></th></tr></thead>
      <tbody>${items.map((i) => html`<tr>
        <td class="nowrap">${fmtDate(i.created_at)}</td>
        <td>${i.student_id ? html`<a href="#/student/${i.student_id}">${i.student_name}</a>` : html`<span class="subtle">unknown</span>`}</td>
        <td><span class="chip">${i.source}</span></td>
        <td class="mono" style="max-width:360px">${Object.entries(i.payload).map(([k, v]) => html`<div>${k}: <b>${v === "" ? "∅ (empty)" : String(v)}</b></div>`)}</td>
        <td>${i.errors.map((e) => html`<div style="margin-bottom:4px"><span class="badge st-weak">${e.field}</span> ${e.message}</div>`)}</td>
        <td><button class="btn sm" data-dismiss="${i.id}">Dismiss</button></td></tr>`)}</tbody></table></div>`
      : empty("No rejected records. All submitted data passed validation.", "✓")}</div>`;

  $$("[data-dismiss]", root).forEach((b) => b.addEventListener("click", async () => {
    await api.dismissIssue(+b.dataset.dismiss);
    toast("Entry dismissed", "success");
    await render(root);
    refreshIssueBadge();
  }));
  $("#clear", root)?.addEventListener("click", async () => {
    if (!(await confirmDialog("Clear the entire data-quality log?", { confirmText: "Clear" }))) return;
    await api.clearIssues();
    toast("Log cleared", "success");
    await render(root);
    refreshIssueBadge();
  });
  return "Data quality";
}
