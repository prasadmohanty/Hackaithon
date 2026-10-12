// Application shell: hash router, theme, API health indicator.
import { api } from "./api.js";
import { config } from "./config.js";
import { bindTips } from "./charts.js";
import { $, $$, errorView, loading } from "./ui.js";

import * as dashboard from "./views/dashboard.js";
import * as students from "./views/students.js";
import * as student from "./views/student.js";
import * as assessments from "./views/assessments.js";
import * as resources from "./views/resources.js";
import * as subjects from "./views/subjects.js";
import * as quality from "./views/quality.js";
import * as rules from "./views/rules.js";
import * as settings from "./views/settings.js";
import * as apiRef from "./views/apiref.js";

const ROUTES = { dashboard, students, student, assessments, resources, subjects, quality, rules, settings, api: apiRef };
const NAV_FOR = { student: "students" };

let renderToken = 0;

export async function navigate() {
  const [name = "dashboard", ...params] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const view = ROUTES[name] || dashboard;
  const root = $("#view");
  const token = ++renderToken;

  $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.route === (NAV_FOR[name] || name)));
  $("#sidebar").classList.remove("open");
  root.innerHTML = loading();

  try {
    const pageTitle = await view.render(root, params, () => token !== renderToken);
    if (token !== renderToken) return;
    $("#page-title").textContent = pageTitle || "Learn4All";
    document.title = `${pageTitle ? pageTitle + " · " : ""}Learn4All`;
    bindTips(root);
  } catch (err) {
    if (token !== renderToken) return;
    console.error(err);
    root.innerHTML = errorView(err, navigate);
  }
  window.scrollTo({ top: 0 });
  refreshIssueBadge();
}

export async function refreshIssueBadge() {
  try {
    const log = await api.validationLog();
    const badge = $("#issue-badge");
    badge.hidden = !log.count;
    badge.textContent = log.count;
  } catch { /* status pill already shows connectivity */ }
}

async function checkHealth() {
  const pill = $("#api-status");
  try {
    const h = await api.health();
    pill.className = "api-status ok";
    pill.querySelector(".label").textContent = `API v${h.version}`;
    pill.title = `Connected to ${config.apiBaseUrl}`;
  } catch {
    pill.className = "api-status down";
    pill.querySelector(".label").textContent = "API offline";
    pill.title = `Cannot reach ${config.apiBaseUrl}`;
  }
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("learn4all.theme"); } catch { /* ignore */ }
  const dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  $("#theme-btn").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("learn4all.theme", next); } catch { /* ignore */ }
  });
}

initTheme();
$("#menu-btn").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
window.addEventListener("hashchange", navigate);
checkHealth();
setInterval(checkHealth, 15000);
navigate();
