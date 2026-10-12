// Small UI toolkit: safe HTML templating, formatting, toasts, modals and form helpers.

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

class SafeHTML {
  constructor(value) { this.value = value; }
  toString() { return this.value; }
}
const part = (v) => (v instanceof SafeHTML ? v.value : esc(v));

/** Tagged template: interpolations are escaped unless they are SafeHTML (nested html`` or raw()). */
export function html(strings, ...values) {
  return new SafeHTML(strings.reduce((out, s, i) => {
    if (i >= values.length) return out + s;
    const v = values[i];
    return out + s + (Array.isArray(v) ? v.map(part).join("") : part(v));
  }, ""));
}
export const raw = (value) => (value instanceof SafeHTML ? value : new SafeHTML(String(value ?? "")));

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ---------- formatting ----------
export const pct = (v, d = 1) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(d)}%`);
export const num = (v, d = 1) => (v === null || v === undefined ? "—" : Number(v).toFixed(d));
export const label = (s) => String(s ?? "").replace(/_/g, " ").replace(/-/g, " ");
export const title = (s) => label(s).replace(/\b\w/g, (c) => c.toUpperCase());
export const initials = (name) => String(name || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
export const fmtDate = (d) => {
  if (!d) return "—";
  const dt = new Date(d.length === 10 ? d + "T00:00:00" : d.replace(" ", "T"));
  return isNaN(dt) ? d : dt.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};

export function scoreColor(v, weak = 60, mastery = 85) {
  if (v === null || v === undefined) return "var(--text-3)";
  if (v < weak) return "var(--danger)";
  if (v < (weak + mastery) / 2) return "var(--amber)";
  if (v < mastery) return "var(--info)";
  return "var(--success)";
}

// ---------- components ----------
export const statusBadge = (s) => html`<span class="badge st-${s}">${label(s)}</span>`;
export const bandBadge = (b) => html`<span class="badge band-${b}">${label(b)}</span>`;
export const priorityBadge = (p) => html`<span class="badge pr-${p}">${p}</span>`;
export const catChip = (c) => html`<span class="chip cat-${c}">${c}</span>`;
export const a11yChips = (list) => (list || []).map((f) => html`<span class="chip a11y">♿ ${f}</span>`);
export function trendLabel(t, slope) {
  const arrow = { improving: "▲", declining: "▼", stable: "▬", insufficient_data: "·" }[t] || "";
  const s = slope !== null && slope !== undefined && t !== "insufficient_data" ? ` ${slope > 0 ? "+" : ""}${Number(slope).toFixed(1)}` : "";
  return html`<span class="trend ${t}">${arrow} ${t === "insufficient_data" ? "not enough data" : label(t)}${s}</span>`;
}
export function scoreBar(v, weak = 60, mastery = 85) {
  const w = Math.max(0, Math.min(100, v ?? 0));
  return html`<div class="score-cell"><div class="bar" style="flex:1">
      <span style="width:${w}%;background:${raw(scoreColor(v, weak, mastery))}"></span>
      <i class="mark" style="left:${weak}%"></i><i class="mark" style="left:${mastery}%"></i>
    </div><b>${pct(v)}</b></div>`;
}
export const avatar = (name, cls = "") => html`<div class="avatar ${cls}" aria-hidden="true">${initials(name)}</div>`;
export const loading = (text = "Loading…") => html`<div class="loading"><div class="spinner"></div>${text}</div>`;
export const empty = (msg, icon = "∅") => html`<div class="empty"><div class="big">${icon}</div>${msg}</div>`;

export function errorView(err, retry) {
  const id = "retry-" + Math.random().toString(36).slice(2);
  setTimeout(() => document.getElementById(id)?.addEventListener("click", retry));
  return html`<div class="card"><div class="empty"><div class="big">⚠</div>
    <h3>Something went wrong</h3><p class="muted">${err.message}</p>
    ${retry ? raw(html`<button class="btn primary" id="${id}">Try again</button>`) : ""}</div></div>`;
}

// ---------- toast ----------
export function toast(message, type = "info", ms = 3500) {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = html`<span>${type === "error" ? "⚠" : type === "success" ? "✓" : "ℹ"}</span><span>${message}</span>`;
  root.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ---------- modal ----------
export function modal({ title: heading, body, submitText = "Save", wide = false, onSubmit, footer = true }) {
  const root = document.getElementById("modal-root");
  const wrap = document.createElement("div");
  wrap.className = "modal-backdrop";
  wrap.innerHTML = html`<div class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <form novalidate>
        <div class="modal-head"><h2 id="modal-title">${heading}</h2>
          <button type="button" class="icon-btn" data-close aria-label="Close">✕</button></div>
        <div class="modal-body">${raw(body)}</div>
        ${footer ? raw(html`<div class="modal-foot"><button type="button" class="btn" data-close>Cancel</button>
          <button type="submit" class="btn primary">${submitText}</button></div>`) : ""}
      </form></div>`;
  const prevFocus = document.activeElement;
  const close = () => { wrap.remove(); document.removeEventListener("keydown", onKey); prevFocus?.focus?.(); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  wrap.addEventListener("mousedown", (e) => { if (e.target === wrap) close(); });
  $$("[data-close]", wrap).forEach((b) => b.addEventListener("click", close));
  const form = $("form", wrap);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!onSubmit) return close();
    const btn = $("button[type=submit]", form);
    btn.disabled = true;
    clearErrors(form);
    try {
      const keepOpen = await onSubmit(form, close);
      if (keepOpen !== true) close();
    } catch (err) {
      showErrors(form, err);
    } finally {
      btn.disabled = false;
    }
  });
  root.appendChild(wrap);
  setTimeout(() => $("input, select, textarea", wrap)?.focus());
  return { el: wrap, form, close };
}

export function confirmDialog(message, { danger = true, confirmText = "Delete" } = {}) {
  return new Promise((resolve) => {
    let ok = false;
    const m = modal({
      title: "Please confirm", body: html`<p style="margin:0">${message}</p>`, submitText: confirmText,
      onSubmit: () => { ok = true; },
    });
    if (danger) $("button[type=submit]", m.form).style.background = "var(--danger)";
    const obs = new MutationObserver(() => { if (!document.body.contains(m.el)) { obs.disconnect(); resolve(ok); } });
    obs.observe(document.getElementById("modal-root"), { childList: true });
  });
}

// ---------- forms ----------
export function field({ name, label: lab, type = "text", value = "", options = null, hint = "", full = false, attrs = "" }) {
  let control;
  if (options) {
    control = html`<select class="input" id="f-${name}" name="${name}" ${raw(attrs)}>${options.map((o) => {
      const [v, t] = Array.isArray(o) ? o : [o, title(o)];
      return raw(html`<option value="${v}" ${String(v) === String(value) ? "selected" : ""}>${t}</option>`);
    })}</select>`;
  } else if (type === "textarea") {
    control = html`<textarea class="input" id="f-${name}" name="${name}" ${raw(attrs)}>${value}</textarea>`;
  } else {
    control = html`<input class="input" id="f-${name}" name="${name}" type="${type}" value="${value}" ${raw(attrs)}>`;
  }
  return html`<div class="field ${full ? "full" : ""}" data-field="${name}"><label for="f-${name}">${lab}</label>${raw(control)}
    ${hint ? raw(html`<span class="hint">${hint}</span>`) : ""}</div>`;
}

export function checkGroup({ name, label: lab, options, selected = [], full = true, hint = "" }) {
  return html`<div class="field ${full ? "full" : ""}" data-field="${name}"><span class="label">${lab}</span><div class="checks">
    ${options.map((o) => {
      const [v, t] = Array.isArray(o) ? o : [o, o];
      return raw(html`<label class="check"><input type="checkbox" name="${name}" value="${v}" ${selected.includes(v) ? "checked" : ""}>${t}</label>`);
    })}</div>${hint ? raw(html`<span class="hint">${hint}</span>`) : ""}</div>`;
}

export function formData(form) {
  const out = {};
  const fd = new FormData(form);
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === "checkbox") out[el.name] = fd.getAll(el.name);
    else out[el.name] = el.value;
  }
  return out;
}

export function clearErrors(form) {
  $$(".err", form).forEach((e) => e.remove());
  $$(".invalid", form).forEach((e) => e.classList.remove("invalid"));
  $$(".form-error", form).forEach((e) => e.remove());
}

export function showErrors(form, err) {
  let general = [];
  (err.details || []).forEach((d) => {
    const wrap = $(`[data-field="${d.field}"]`, form);
    if (wrap) {
      $(".input", wrap)?.classList.add("invalid");
      wrap.insertAdjacentHTML("beforeend", html`<span class="err">${d.message}</span>`);
    } else general.push(`${d.field}: ${d.message}`);
  });
  if (!err.details?.length || general.length) {
    $(".modal-body", form)?.insertAdjacentHTML("afterbegin",
      html`<div class="callout danger form-error" style="margin-bottom:14px"><b>${err.message}</b>${general.length ? raw("<br>" + general.map(esc).join("<br>")) : ""}</div>`);
  }
}

export function downloadJSON(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: filename });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
