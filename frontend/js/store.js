// Cached reference data shared by views (vocabularies, settings, subjects/topics, students).
import { api } from "./api.js";

export const store = {
  meta: null,
  settings: null,
  subjects: null,
  students: null,

  async ensure({ meta = false, settings = false, subjects = false, students = false } = {}) {
    const jobs = [];
    if (meta && !this.meta) jobs.push(api.meta().then((m) => (this.meta = m)));
    if (settings && !this.settings) jobs.push(api.settings().then((s) => (this.settings = s.values)));
    if (subjects && !this.subjects) jobs.push(api.subjects().then((s) => (this.subjects = s.items)));
    if (students && !this.students) jobs.push(api.students().then((s) => (this.students = s.items)));
    await Promise.all(jobs);
    return this;
  },

  invalidate(...keys) {
    (keys.length ? keys : ["meta", "settings", "subjects", "students"]).forEach((k) => (this[k] = null));
  },

  get weak() { return this.settings?.weak_threshold ?? 60; },
  get mastery() { return this.settings?.mastery_threshold ?? 85; },

  topics() {
    return (this.subjects || []).flatMap((s) => s.topics.map((t) => ({ ...t, subject_name: s.name, subject_code: s.code })));
  },
};
