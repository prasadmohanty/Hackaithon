// Assessment records: filter, add, edit, delete and bulk CSV import.
import { api } from "../api.js";
import { assessmentDialog } from "../forms.js";
import { store } from "../store.js";
import { $, $$, confirmDialog, empty, field, fmtDate, html, modal, num, pct, scoreColor, title, toast } from "../ui.js";

const SAMPLE_CSV = `student_email,subject_code,topic_name,date,score,max_score,assessment_type,notes
mira@learn4all.example,PY101,Loops,${new Date().toISOString().slice(0, 10)},64,100,quiz,Retest after practice
sara@learn4all.example,ENG8,Grammar,${new Date().toISOString().slice(0, 10)},58,100,test,
leo@learn4all.example,PY101,Loops,2026-13-45,90,100,quiz,Invalid date example
zoya@learn4all.example,PY101,Functions,${new Date().toISOString().slice(0, 10)},120,100,test,Score above max example`;

export async function render(root) {
  await store.ensure({ subjects: true, students: true, settings: true, meta: true });
  const topics = store.topics();
  root.innerHTML = html`
    <div class="page-head">
      <div><h1>Assessments</h1><p>Historical assessment records. Invalid, duplicate or inconsistent entries are rejected by the API.</p></div>
      <div class="row"><button class="btn" id="bulk">⇪ Bulk import (CSV)</button><button class="btn primary" id="add">＋ Record assessment</button></div>
    </div>
    <div class="toolbar">
      <select class="input" id="f-student" aria-label="Filter by learner"><option value="">All learners</option>
        ${store.students.map((s) => html`<option value="${s.id}">${s.name}</option>`)}</select>
      <select class="input" id="f-subject" aria-label="Filter by subject"><option value="">All subjects</option>
        ${store.subjects.map((s) => html`<option value="${s.id}">${s.name}</option>`)}</select>
      <select class="input" id="f-topic" aria-label="Filter by topic"><option value="">All topics</option></select>
      <input class="input" type="date" id="f-from" aria-label="From date"><input class="input" type="date" id="f-to" aria-label="To date">
      <span class="spacer"></span><span class="subtle" id="count"></span>
    </div>
    <div class="card flush"><div id="list"></div></div>`;

  const fillTopics = () => {
    const sid = $("#f-subject", root).value;
    $("#f-topic", root).innerHTML = html`<option value="">All topics</option>${topics.filter((t) => !sid || String(t.subject_id) === sid)
      .map((t) => html`<option value="${t.id}">${t.name}</option>`)}`;
  };
  fillTopics();

  const load = async () => {
    const { items } = await api.assessments({
      student_id: $("#f-student", root).value, subject_id: $("#f-subject", root).value, topic_id: $("#f-topic", root).value,
      from: $("#f-from", root).value, to: $("#f-to", root).value,
    });
    $("#count", root).textContent = `${items.length} record(s)`;
    const list = $("#list", root);
    list.innerHTML = items.length ? html`<div class="table-wrap"><table class="table">
      <thead><tr><th>Date</th><th>Learner</th><th>Subject</th><th>Topic</th><th>Type</th><th class="num">Score</th><th class="num">Percent</th><th>Notes</th><th></th></tr></thead>
      <tbody>${[...items].reverse().map((a) => html`<tr>
        <td class="nowrap">${fmtDate(a.date)}</td><td><a href="#/student/${a.student_id}">${a.student_name}</a></td>
        <td>${a.subject_name}</td><td>${a.topic_name}</td><td>${title(a.assessment_type)}</td>
        <td class="num">${num(a.score, 1)} / ${num(a.max_score, 0)}</td>
        <td class="num"><b style="color:${scoreColor(a.percentage, store.weak, store.mastery)}">${pct(a.percentage)}</b></td>
        <td class="subtle">${a.notes}</td>
        <td class="nowrap"><button class="btn sm ghost" data-edit="${a.id}" aria-label="Edit">✎</button>
          <button class="btn sm ghost danger" data-del="${a.id}" aria-label="Delete">🗑</button></td></tr>`)}</tbody></table></div>`
      : empty("No assessments match these filters.", "✎");
    $$("[data-edit]", list).forEach((b) => b.addEventListener("click", () =>
      assessmentDialog({ existing: items.find((a) => a.id === +b.dataset.edit), onSaved: load })));
    $$("[data-del]", list).forEach((b) => b.addEventListener("click", async () => {
      if (!(await confirmDialog("Delete this assessment record?"))) return;
      await api.deleteAssessment(+b.dataset.del);
      toast("Assessment deleted", "success");
      load();
    }));
  };

  $("#f-subject", root).addEventListener("change", () => { fillTopics(); load(); });
  ["#f-student", "#f-topic", "#f-from", "#f-to"].forEach((s) => $(s, root).addEventListener("change", load));
  $("#add", root).addEventListener("click", () => assessmentDialog({ studentId: $("#f-student", root).value || null, onSaved: load }));
  $("#bulk", root).addEventListener("click", () => bulkDialog(load));
  await load();
  return "Assessments";
}

function bulkDialog(onDone) {
  const m = modal({
    title: "Bulk import assessments", submitText: "Validate & import", wide: true,
    body: html`<p class="muted" style="margin-top:0">Paste CSV with a header row. Use <code>student_email</code> or <code>student_id</code>,
      and <code>topic_id</code> or <code>subject_code</code> + <code>topic_name</code>. Each row is validated separately —
      valid rows are saved, invalid rows are rejected and written to the data-quality log.</p>
      ${field({ name: "csv", label: "CSV data", type: "textarea", value: SAMPLE_CSV, full: true, attrs: "rows='8' spellcheck='false'" })}
      <div id="bulk-result" style="margin-top:14px"></div>`,
    async onSubmit(form) {
      const res = await api.bulkAssessments({ csv: $("[name=csv]", form).value });
      $("#bulk-result", form).innerHTML = html`<div class="callout ${res.rejected ? "warn" : "ok"}">
          <b>${res.accepted} of ${res.total} rows imported</b>, ${res.rejected} rejected.</div>
        <div class="table-wrap" style="margin-top:10px"><table class="table"><thead><tr><th>Row</th><th>Status</th><th>Details</th></tr></thead>
        <tbody>${res.results.map((r) => html`<tr><td>${r.row}</td>
          <td>${r.status === "created" ? html`<span class="badge st-mastered">created #${r.id}</span>` : html`<span class="badge st-weak">${r.code}</span>`}</td>
          <td>${(r.errors || []).map((e) => html`<div><b>${e.field}</b>: ${e.message}</div>`)}</td></tr>`)}</tbody></table></div>`;
      if (res.accepted) toast(`${res.accepted} assessment(s) imported`, "success");
      onDone();
      return true; // keep dialog open to show per-row results
    },
  });
  return m;
}
