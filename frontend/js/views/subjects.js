// Subjects and their topics.
import { api } from "../api.js";
import { store } from "../store.js";
import { $, $$, confirmDialog, empty, field, formData, html, modal, toast } from "../ui.js";

export async function render(root) {
  const { items } = await api.subjects();
  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Subjects &amp; topics</h1><p>Topics are the unit of analysis: assessments and resources are linked to a topic.</p></div>
      <button class="btn primary" id="add">＋ Add subject</button>
    </div>
    <div class="grid grid-3">${items.length ? items.map((s) => html`<article class="card">
      <div class="card-head"><div><span class="chip mono">${s.code}</span>
        <h3 style="margin-top:8px;font-size:17px">${s.name}</h3><p>${s.description}</p></div>
        <div class="nowrap"><button class="btn sm ghost" data-edit="${s.id}" aria-label="Edit subject">✎</button>
          <button class="btn sm ghost danger" data-del="${s.id}" aria-label="Delete subject">🗑</button></div></div>
      ${s.topics.map((t) => html`<div class="topic-pill"><span class="t">${t.name}</span>
        <span class="nowrap"><button class="btn sm ghost" data-rt="${t.id}" aria-label="Rename topic">✎</button>
        <button class="btn sm ghost danger" data-dt="${t.id}" aria-label="Delete topic">✕</button></span></div>`)}
      <form class="row" data-topic-form="${s.id}" style="margin-top:12px;flex-wrap:nowrap">
        <input class="input" name="name" placeholder="New topic name" aria-label="New topic name" required>
        <button class="btn" type="submit">Add</button></form>
    </article>`) : html`<div class="card">${empty("No subjects yet.")}</div>`}</div>`;

  const reload = () => { store.invalidate("subjects"); return render(root); };
  const subjectDialog = (s) => modal({
    title: s ? "Edit subject" : "Add subject", submitText: s ? "Save" : "Add subject",
    body: html`<div class="form-grid">
      ${field({ name: "code", label: "Code *", value: s?.code || "", hint: "e.g. SCI8 — letters, digits, - or _" })}
      ${field({ name: "name", label: "Name *", value: s?.name || "" })}
      ${field({ name: "description", label: "Description", value: s?.description || "", full: true })}
      ${s ? "" : field({ name: "topics", label: "Topics (comma separated)", value: "", full: true })}</div>`,
    async onSubmit(form) {
      const d = formData(form);
      if (!s) d.topics = (d.topics || "").split(",").map((x) => x.trim()).filter(Boolean);
      s ? await api.updateSubject(s.id, d) : await api.createSubject(d);
      toast("Subject saved", "success");
      reload();
    },
  });

  $("#add", root).addEventListener("click", () => subjectDialog(null));
  $$("[data-edit]", root).forEach((b) => b.addEventListener("click", () => subjectDialog(items.find((s) => s.id === +b.dataset.edit))));
  $$("[data-del]", root).forEach((b) => b.addEventListener("click", async () => {
    const s = items.find((x) => x.id === +b.dataset.del);
    if (!(await confirmDialog(`Delete ${s.name}? Its topics, assessments and resources will be deleted too.`))) return;
    await api.deleteSubject(s.id);
    toast("Subject deleted", "success");
    reload();
  }));
  $$("[data-topic-form]", root).forEach((f) => f.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api.createTopic(+f.dataset.topicForm, { name: f.elements.name.value });
      toast("Topic added", "success");
      reload();
    } catch (err) { toast(err.details?.[0]?.message || err.message, "error"); }
  }));
  const allTopics = items.flatMap((s) => s.topics);
  $$("[data-rt]", root).forEach((b) => b.addEventListener("click", () => {
    const t = allTopics.find((x) => x.id === +b.dataset.rt);
    modal({
      title: "Rename topic", body: field({ name: "name", label: "Topic name", value: t.name }),
      async onSubmit(form) { await api.updateTopic(t.id, formData(form)); toast("Topic renamed", "success"); reload(); },
    });
  }));
  $$("[data-dt]", root).forEach((b) => b.addEventListener("click", async () => {
    const t = allTopics.find((x) => x.id === +b.dataset.dt);
    if (!(await confirmDialog(`Delete topic “${t.name}”? Its assessments and resources will be deleted.`))) return;
    await api.deleteTopic(t.id);
    toast("Topic deleted", "success");
    reload();
  }));
  return "Subjects & topics";
}
