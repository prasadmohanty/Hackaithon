// Live API reference generated from GET /api/docs — useful for anyone building another frontend.
import { api } from "../api.js";
import { config } from "../config.js";
import { html } from "../ui.js";

export async function render(root) {
  const { endpoints } = await api.docs();
  const groups = {};
  endpoints.forEach((e) => (groups[e.tag] = groups[e.tag] || []).push(e));
  root.innerHTML = html`
    <div class="page-head"><div><h1>API reference</h1>
      <p>Generated live from the backend. Build any frontend (web, mobile, CLI) against these endpoints.</p></div>
      <a class="btn" href="${config.apiBaseUrl}/api/openapi.json" target="_blank" rel="noopener">OpenAPI JSON ↗</a></div>
    <div class="card" style="margin-bottom:18px"><dl class="kv">
      <dt>Base URL</dt><dd><code>${config.apiBaseUrl}</code></dd>
      <dt>Format</dt><dd>JSON request and response bodies (UTF-8). CORS enabled.</dd>
      <dt>Collections</dt><dd><code>{"items": [...], "count": n}</code></dd>
      <dt>Errors</dt><dd><code>{"error": {"code", "message", "details": [{"field", "message"}]}}</code> with 400 / 404 / 405 / 409 / 422 / 500</dd>
    </dl></div>
    <div class="stack">${Object.entries(groups).map(([tag, list]) => html`<div class="card flush">
      <div class="card-head" style="padding-bottom:12px"><div class="section-title">${tag} <span class="count">${list.length}</span></div></div>
      <div class="table-wrap"><table class="table"><tbody>${list.map((e) => html`<tr>
        <td style="width:80px"><span class="method m-${e.method}">${e.method}</span></td>
        <td class="mono nowrap">${e.path}</td>
        <td>${e.summary}${e.query.length ? html`<div class="subtle">Query: ${e.query.map((q) => html`<code>${q.name}</code> ${q.description}; `)}</div>` : ""}
          ${e.body ? html`<details class="trace"><summary>Example body</summary><pre class="code">${JSON.stringify(e.body, null, 2)}</pre></details>` : ""}</td>
        <td class="subtle nowrap">→ ${e.success_status}</td></tr>`)}</tbody></table></div></div>`)}</div>`;
  return "API reference";
}
