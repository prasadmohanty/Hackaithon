// Thin client for the Learn4All REST API. Every backend call in the UI goes through here.
import { config } from "./config.js";

export class ApiError extends Error {
  constructor(status, error) {
    super(error?.message || `Request failed (${status})`);
    this.status = status;
    this.code = error?.code;
    this.details = error?.details || [];
  }
}

async function request(method, path, body, query) {
  const url = new URL(config.apiBaseUrl + path);
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError(0, { code: "network", message: `Cannot reach the API at ${config.apiBaseUrl}. Is the backend running?` });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data.error);
  return data;
}

const get = (p, q) => request("GET", p, undefined, q);
const post = (p, b) => request("POST", p, b ?? {});
const put = (p, b) => request("PUT", p, b);
const del = (p, q) => request("DELETE", p, undefined, q);

export const api = {
  health: () => get("/api/health"),
  meta: () => get("/api/meta"),
  docs: () => get("/api/docs"),
  resetDemo: () => post("/api/admin/reset"),

  settings: () => get("/api/settings"),
  updateSettings: (values) => put("/api/settings", values),
  resetSettings: () => post("/api/settings/reset"),
  rules: () => get("/api/rules"),

  students: (search) => get("/api/students", { search }),
  student: (id) => get(`/api/students/${id}`),
  createStudent: (b) => post("/api/students", b),
  updateStudent: (id, b) => put(`/api/students/${id}`, b),
  deleteStudent: (id) => del(`/api/students/${id}`),
  performance: (id) => get(`/api/students/${id}/performance`),
  recommendations: (id) => get(`/api/students/${id}/recommendations`),
  report: (id) => get(`/api/students/${id}/report`),

  subjects: () => get("/api/subjects"),
  createSubject: (b) => post("/api/subjects", b),
  updateSubject: (id, b) => put(`/api/subjects/${id}`, b),
  deleteSubject: (id) => del(`/api/subjects/${id}`),
  topics: (subject_id) => get("/api/topics", { subject_id }),
  createTopic: (subjectId, b) => post(`/api/subjects/${subjectId}/topics`, b),
  updateTopic: (id, b) => put(`/api/topics/${id}`, b),
  deleteTopic: (id) => del(`/api/topics/${id}`),

  assessments: (q) => get("/api/assessments", q),
  createAssessment: (b) => post("/api/assessments", b),
  bulkAssessments: (b) => post("/api/assessments/bulk", b),
  updateAssessment: (id, b) => put(`/api/assessments/${id}`, b),
  deleteAssessment: (id) => del(`/api/assessments/${id}`),

  resources: (q) => get("/api/resources", q),
  createResource: (b) => post("/api/resources", b),
  updateResource: (id, b) => put(`/api/resources/${id}`, b),
  deleteResource: (id) => del(`/api/resources/${id}`),

  classReport: () => get("/api/reports/class"),
  validationLog: (student_id) => get("/api/validation-log", { student_id }),
  dismissIssue: (id) => del(`/api/validation-log/${id}`),
  clearIssues: (student_id) => del("/api/validation-log", { student_id }),
};
