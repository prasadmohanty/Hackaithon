// Learning resource catalogue with filters and CRUD.
import { api } from "../api.js";
import { resourceDialog } from "../forms.js";
import { store } from "../store.js";
import { $, $$, a11yChips, catChip, confirmDialog, empty, html, title, toast } from "../ui.js";

const ICON = { video: "▶", notes: "📄", quiz: "❓", practice: "🛠" };

export async function render(root) {
  await store.ensure({ meta: true, subjects: true });
  const m = store.meta;
  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Learning resources</h1><p>Videos, notes, quizzes and practice tasks — each with difficulty, time and accessibility formats.</p></div>
      <button class="btn primary" id="add">＋ Add resource</button>
    </div>
    <div class="toolbar">
      <input class="input search" type="search" id="q" placeholder="Search resources…" aria-label="Search resources">
      <select class="input" id="subject" aria-label="Subject"><option value="">All subjects</option>${store.subjects.map((s) => html`<option value="${s.id}">${s.name}</option>`)}</select>
      <select class="input" id="category" aria-label="Category"><option value="">All categories</option>${m.resource_categories.map((c) => html`<option value="${c}">${title(c)}</option>`)}</select>
      <select class="input" id="difficulty" aria-label="Difficulty"><option value="">All levels</option>${m.difficulty_levels.map((c) => html`<option value="${c}">${title(c)}</option>`)}</select>
      <select class="input" id="format" aria-label="Accessibility format"><option value="">Any accessibility</option>${m.accessibility_formats.map((f) => html`<option value="${f.code}">♿ ${f.code}</option>`)}</select>
      <span class="spacer"></span><span class="subtle" id="count"></span>
    </div>
    <div id="list" class="grid grid-3"></div>`;

  let timer;
  const load = async () => {
    const { items } = await api.resources({
      search: $("#q", root).value, subject_id: $("#subject", root).value, category: $("#category", root).value,
      difficulty: $("#difficulty", root).value, format: $("#format", root).value,
    });
    $("#count", root).textContent = `${items.length} resource(s)`;
    const list = $("#list", root);
    list.innerHTML = items.length ? html`${items.map((r) => html`<article class="card" style="display:flex;flex-direction:column;gap:10px">
        <div class="row" style="justify-content:space-between">${catChip(r.category)}<span class="subtle">${ICON[r.category] || ""} ${r.learning_mode}</span></div>
        <div><div class="rec-title">${r.url ? html`<a href="${r.url}" target="_blank" rel="noopener">${r.title}</a>` : r.title}</div>
          <div class="subtle">${r.subject_name} · ${r.topic_name}</div></div>
        <div class="muted" style="font-size:13px;flex:1">${r.description}</div>
        <div class="row" style="gap:6px"><span class="chip">${r.difficulty}</span><span class="chip">⏱ ${r.estimated_minutes} min</span></div>
        <div class="row" style="gap:6px">${r.formats.length ? a11yChips(r.formats) : html`<span class="subtle">No accessibility formats</span>`}</div>
        <div class="row" style="justify-content:flex-end"><button class="btn sm" data-edit="${r.id}">✎ Edit</button>
          <button class="btn sm danger" data-del="${r.id}">Delete</button></div>
      </article>`)}` : html`<div class="card span-2">${empty("No resources match these filters.", "▤")}</div>`;
    $$("[data-edit]", list).forEach((b) => b.addEventListener("click", () => resourceDialog(items.find((r) => r.id === +b.dataset.edit), load)));
    $$("[data-del]", list).forEach((b) => b.addEventListener("click", async () => {
      const r = items.find((x) => x.id === +b.dataset.del);
      if (!(await confirmDialog(`Delete “${r.title}”?`))) return;
      await api.deleteResource(r.id);
      toast("Resource deleted", "success");
      load();
    }));
  };
  $("#q", root).addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
  ["#subject", "#category", "#difficulty", "#format"].forEach((s) => $(s, root).addEventListener("change", load));
  $("#add", root).addEventListener("click", () => resourceDialog(null, load));
  await load();
  return "Resources";
}
