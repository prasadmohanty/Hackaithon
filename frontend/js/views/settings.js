// Analysis settings (server-side) + frontend connection settings (browser-side).
import { api } from "../api.js";
import { config } from "../config.js";
import { store } from "../store.js";
import { $, clearErrors, confirmDialog, field, formData, html, showErrors, toast } from "../ui.js";

const GROUPS = [
  ["Thresholds & evidence", ["weak_threshold", "mastery_threshold", "min_evidence", "trend_threshold"]],
  ["Weighted performance", ["recency_weight", "weight_quiz", "weight_assignment", "weight_test", "weight_exam"]],
  ["Recommendations", ["max_recommendations", "max_per_topic"]],
];

export async function render(root) {
  const { spec } = await api.settings();
  root.innerHTML = html`
    <div class="page-head"><div><h1>Settings</h1><p>Configurable thresholds and weights. Changes apply instantly to every report.</p></div></div>
    <form id="settings" class="stack" novalidate>
      ${GROUPS.map(([name, keys]) => html`<div class="card"><div class="section-title" style="margin-bottom:14px">${name}</div>
        <div class="form-grid">${keys.map((k) => field({ name: k, label: spec[k].label, type: "number", value: spec[k].value,
          hint: `${spec[k].description} (${spec[k].min}–${spec[k].max})`, attrs: `step="${spec[k].type === "int" ? 1 : "any"}" min="${spec[k].min}" max="${spec[k].max}"` }))}</div></div>`)}
      <div class="row"><button class="btn primary" type="submit">Save settings</button><button class="btn" type="button" id="defaults">Restore defaults</button></div>
    </form>

    <div class="grid grid-2" style="margin-top:22px">
      <div class="card"><div class="section-title" style="margin-bottom:6px">API connection (this browser)</div>
        <p class="subtle" style="margin-top:0">The frontend is a separate app; it only knows the API base URL.</p>
        <form id="conn" class="row" style="flex-wrap:nowrap"><input class="input" name="url" value="${config.apiBaseUrl}" aria-label="API base URL">
          <button class="btn" type="submit">Connect</button></form></div>
      <div class="card"><div class="section-title" style="margin-bottom:6px">Demo data</div>
        <p class="subtle" style="margin-top:0">Erase everything and reload the representative sample (8 learners, 3 subjects, 45 resources, invalid records).</p>
        <button class="btn danger" id="reset">Reset sample data</button></div>
    </div>`;

  const form = $("#settings", root);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors(form);
    try {
      const values = Object.fromEntries(Object.entries(formData(form)).map(([k, v]) => [k, v === "" ? null : Number(v)]));
      await api.updateSettings(values);
      store.invalidate("settings");
      toast("Settings saved — reports recalculated", "success");
    } catch (err) {
      showErrors(form, err);
      toast(err.message, "error");
    }
  });
  $("#defaults", root).addEventListener("click", async () => {
    await api.resetSettings();
    store.invalidate("settings");
    toast("Defaults restored", "success");
    render(root);
  });
  $("#conn", root).addEventListener("submit", (e) => {
    e.preventDefault();
    config.setApiBaseUrl(e.target.url.value.trim());
    location.reload();
  });
  $("#reset", root).addEventListener("click", async () => {
    if (!(await confirmDialog("Erase all data and reload the sample data set?", { confirmText: "Reset" }))) return;
    const res = await api.resetDemo();
    store.invalidate();
    toast(`Sample data loaded: ${res.students} learners, ${res.assessments_created} assessments`, "success");
    location.hash = "#/dashboard";
  });
  return "Settings";
}
