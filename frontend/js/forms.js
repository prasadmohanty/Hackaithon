// Reusable create/edit dialogs for learners, assessments and resources.
import { api } from "./api.js";
import { store } from "./store.js";
import { $, checkGroup, field, formData, html, modal, title, toast } from "./ui.js";

export async function studentDialog(existing, onSaved) {
  await store.ensure({ meta: true });
  const s = existing || { weekly_study_minutes: 120, accessibility_needs: [], preferred_categories: [] };
  modal({
    title: existing ? `Edit ${existing.name}` : "Add learner",
    submitText: existing ? "Save changes" : "Add learner",
    body: html`<div class="form-grid">
      ${field({ name: "name", label: "Full name *", value: s.name || "", attrs: "required autocomplete='off'" })}
      ${field({ name: "email", label: "Email", type: "email", value: s.email || "" })}
      ${field({ name: "grade_level", label: "Grade / class", value: s.grade_level || "" })}
      ${field({ name: "weekly_study_minutes", label: "Weekly study time (minutes)", type: "number", value: s.weekly_study_minutes, attrs: "min='0' max='10080'" })}
      ${checkGroup({ name: "accessibility_needs", label: "Accessibility needs",
        options: store.meta.accessibility_formats.map((f) => [f.code, f.code]), selected: s.accessibility_needs,
        hint: "Resources must support each need that applies to their format." })}
      ${checkGroup({ name: "preferred_categories", label: "Preferred resource types",
        options: store.meta.resource_categories.map((c) => [c, title(c)]), selected: s.preferred_categories })}
      ${field({ name: "notes", label: "Notes", type: "textarea", value: s.notes || "", full: true })}
    </div>`,
    async onSubmit(form) {
      const data = formData(form);
      data.weekly_study_minutes = data.weekly_study_minutes === "" ? 120 : Number(data.weekly_study_minutes);
      const saved = existing ? await api.updateStudent(existing.id, data) : await api.createStudent(data);
      store.invalidate("students");
      toast(existing ? "Learner updated" : `${saved.name} added`, "success");
      onSaved?.(saved);
    },
  });
}

export async function assessmentDialog({ existing = null, studentId = null, onSaved } = {}) {
  await store.ensure({ meta: true, subjects: true, students: true });
  const a = existing || { date: new Date().toISOString().slice(0, 10), max_score: 100, assessment_type: "test", student_id: studentId };
  const topics = store.topics();
  const subjectId = a.subject_id || topics.find((t) => t.id === a.topic_id)?.subject_id || store.subjects[0]?.id;
  const m = modal({
    title: existing ? "Edit assessment" : "Record assessment",
    submitText: existing ? "Save changes" : "Save assessment",
    body: html`<div class="form-grid">
      ${field({ name: "student_id", label: "Learner *", value: a.student_id ?? "", full: true,
        options: [["", "Select learner…"], ...store.students.map((s) => [s.id, s.name])] })}
      ${field({ name: "subject_id", label: "Subject *", value: subjectId, options: store.subjects.map((s) => [s.id, s.name]) })}
      ${field({ name: "topic_id", label: "Topic *", value: a.topic_id ?? "", options: [["", "Select topic…"]] })}
      ${field({ name: "date", label: "Date *", type: "date", value: a.date })}
      ${field({ name: "assessment_type", label: "Type", value: a.assessment_type, options: store.meta.assessment_types })}
      ${field({ name: "score", label: "Score *", type: "number", value: a.score ?? "", attrs: "step='any'" })}
      ${field({ name: "max_score", label: "Max score", type: "number", value: a.max_score, attrs: "step='any'" })}
      ${field({ name: "notes", label: "Notes", value: a.notes || "", full: true })}
      <div class="full callout">Records are validated by the API: missing fields, invalid scores, future dates, duplicates
        (same learner + topic + date + type) and inconsistent data (e.g. score above max) are rejected and logged.</div>
    </div>`,
    async onSubmit(form) {
      const data = formData(form);
      const saved = existing ? await api.updateAssessment(existing.id, data) : await api.createAssessment(data);
      toast(`Saved: ${saved.student_name} · ${saved.topic_name} · ${saved.percentage}%`, "success");
      onSaved?.(saved);
    },
  });
  const subjSel = $("[name=subject_id]", m.form), topicSel = $("[name=topic_id]", m.form);
  const fillTopics = (keep) => {
    const list = topics.filter((t) => String(t.subject_id) === subjSel.value);
    topicSel.innerHTML = html`<option value="">Select topic…</option>${list.map((t) =>
      html`<option value="${t.id}" ${String(t.id) === String(keep) ? "selected" : ""}>${t.name}</option>`)}`;
  };
  subjSel.addEventListener("change", () => fillTopics());
  fillTopics(a.topic_id);
}

export async function resourceDialog(existing, onSaved) {
  await store.ensure({ meta: true, subjects: true });
  const r = existing || { category: "notes", difficulty: "beginner", estimated_minutes: 15, formats: [] };
  const topics = store.topics();
  modal({
    title: existing ? "Edit resource" : "Add learning resource",
    submitText: existing ? "Save changes" : "Add resource",
    wide: true,
    body: html`<div class="form-grid">
      ${field({ name: "title", label: "Title *", value: r.title || "", full: true })}
      ${field({ name: "topic_id", label: "Topic *", value: r.topic_id ?? "",
        options: [["", "Select topic…"], ...topics.map((t) => [t.id, `${t.subject_name} — ${t.name}`])] })}
      ${field({ name: "category", label: "Category *", value: r.category, options: store.meta.resource_categories })}
      ${field({ name: "difficulty", label: "Difficulty *", value: r.difficulty, options: store.meta.difficulty_levels })}
      ${field({ name: "estimated_minutes", label: "Estimated time (minutes) *", type: "number", value: r.estimated_minutes })}
      ${checkGroup({ name: "formats", label: "Accessibility formats supported",
        options: store.meta.accessibility_formats.map((f) => [f.code, f.code]), selected: r.formats })}
      ${field({ name: "url", label: "Link (URL)", value: r.url || "", full: true, attrs: "placeholder='https://'" })}
      ${field({ name: "description", label: "Description", type: "textarea", value: r.description || "", full: true })}
    </div>`,
    async onSubmit(form) {
      const data = formData(form);
      const saved = existing ? await api.updateResource(existing.id, data) : await api.createResource(data);
      toast(existing ? "Resource updated" : `“${saved.title}” added`, "success");
      onSaved?.(saved);
    },
  });
}
