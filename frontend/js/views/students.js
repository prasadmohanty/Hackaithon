// Learner directory with search, add, edit and delete.
import { api } from "../api.js";
import { studentDialog } from "../forms.js";
import { store } from "../store.js";
import { $, $$, a11yChips, avatar, bandBadge, confirmDialog, empty, html, scoreBar, toast, trendLabel } from "../ui.js";

export async function render(root) {
  await store.ensure({ settings: true });
  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Learners</h1><p>Every learner's progress at a glance. Open a learner for the full report and study plan.</p></div>
      <button class="btn primary" id="add">＋ Add learner</button>
    </div>
    <div class="toolbar"><input class="input search" id="q" type="search" placeholder="Search by name or email…" aria-label="Search learners"></div>
    <div class="card flush"><div id="list"></div></div>`;

  const list = $("#list", root);
  let timer;
  const load = async () => {
    const { items } = await api.students($("#q", root).value);
    list.innerHTML = items.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th>Learner</th><th>Grade</th><th style="min-width:170px">Overall</th><th>Trend</th><th class="num">Gaps</th><th class="num">Strengths</th><th>Accessibility</th><th>Band</th><th></th></tr></thead>
      <tbody>${items.map((s) => html`<tr>
        <td><a class="person" href="#/student/${s.id}" style="color:inherit">${avatar(s.name)}<div><div class="n">${s.name}</div><div class="subtle">${s.email || "no email"}</div></div></a></td>
        <td class="nowrap">${s.grade_level || "—"}</td>
        <td>${scoreBar(s.summary.overall_average, store.weak, store.mastery)}</td>
        <td>${trendLabel(s.summary.trend)}</td>
        <td class="num">${s.summary.gap_count}</td>
        <td class="num">${s.summary.strength_count}</td>
        <td><div class="row" style="gap:5px">${s.accessibility_needs.length ? a11yChips(s.accessibility_needs) : html`<span class="subtle">—</span>`}</div></td>
        <td>${bandBadge(s.summary.band)}</td>
        <td class="nowrap"><a class="btn sm" href="#/student/${s.id}">Report</a>
          <button class="btn sm ghost" data-edit="${s.id}" aria-label="Edit ${s.name}">✎</button>
          <button class="btn sm ghost danger" data-del="${s.id}" aria-label="Delete ${s.name}">🗑</button></td>
      </tr>`)}</tbody></table></div>` : empty("No learners found. Add your first learner to get started.", "☺");

    $$("[data-edit]", list).forEach((b) => b.addEventListener("click", () =>
      studentDialog(items.find((s) => s.id === +b.dataset.edit), load)));
    $$("[data-del]", list).forEach((b) => b.addEventListener("click", async () => {
      const s = items.find((x) => x.id === +b.dataset.del);
      if (!(await confirmDialog(`Delete ${s.name}? All of their assessments will also be deleted.`))) return;
      await api.deleteStudent(s.id);
      store.invalidate("students");
      toast(`${s.name} deleted`, "success");
      load();
    }));
  };

  $("#q", root).addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
  $("#add", root).addEventListener("click", () => studentDialog(null, (s) => (location.hash = `#/student/${s.id}`)));
  await load();
  return "Learners";
}
