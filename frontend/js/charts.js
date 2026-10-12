// Dependency-free SVG charts (line, bar, donut, sparkline) with hover tooltips.
import { esc, html, raw } from "./ui.js";

export const PALETTE = ["#6366f1", "#0ea5a4", "#f59e0b", "#ec4899", "#22c55e", "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16", "#f97316"];

let tipEl;
function tip() {
  if (!tipEl) {
    tipEl = document.createElement("div");
    tipEl.className = "chart-tip";
    document.body.appendChild(tipEl);
  }
  return tipEl;
}
/** Wire hover tooltips for any element with data-tip inside root. */
export function bindTips(root) {
  root.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("mouseenter", () => { const t = tip(); t.innerHTML = el.dataset.tip; t.style.opacity = 1; });
    el.addEventListener("mousemove", (e) => { const t = tip(); t.style.left = e.clientX + 12 + "px"; t.style.top = e.clientY - 34 + "px"; });
    el.addEventListener("mouseleave", () => { tip().style.opacity = 0; });
  });
}

const thresholdLines = (thresholds, x0, x1, y) => thresholds.map((t) => html`
  <line class="threshold" x1="${x0}" x2="${x1}" y1="${y(t.value)}" y2="${y(t.value)}" stroke="${t.color}"/>
  <text x="${x1 - 4}" y="${y(t.value) - 5}" text-anchor="end" font-size="10.5" fill="${t.color}" font-weight="600">${t.label}</text>`);

/**
 * Multi-series line chart over dates.
 * series: [{name, color?, points: [{date: 'YYYY-MM-DD', value: number}]}]
 */
export function lineChart(series, { height = 260, thresholds = [], yMax = 100 } = {}) {
  const all = series.flatMap((s) => s.points);
  if (!all.length) return html`<div class="empty">No history yet</div>`;
  const W = 720, H = height, P = { l: 40, r: 16, t: 14, b: 30 };
  const times = all.map((p) => +new Date(p.date));
  let tMin = Math.min(...times), tMax = Math.max(...times);
  if (tMin === tMax) { tMin -= 86400000 * 3; tMax += 86400000 * 3; }
  const x = (d) => P.l + ((+new Date(d) - tMin) / (tMax - tMin)) * (W - P.l - P.r);
  const y = (v) => P.t + (1 - v / yMax) * (H - P.t - P.b);
  const ticks = [0, 25, 50, 75, 100];
  const dates = [...new Set(all.map((p) => p.date))].sort();
  const step = Math.max(1, Math.ceil(dates.length / 6));
  const lines = series.map((s, i) => {
    const color = s.color || PALETTE[i % PALETTE.length];
    const pts = [...s.points].sort((a, b) => a.date.localeCompare(b.date));
    const d = pts.map((p, j) => `${j ? "L" : "M"}${x(p.date).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
    const area = pts.length > 1 && series.length === 1
      ? html`<path d="${d} L${x(pts[pts.length - 1].date)},${y(0)} L${x(pts[0].date)},${y(0)} Z" fill="${color}" opacity=".08"/>` : "";
    return html`${area}<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      ${pts.map((p) => html`<circle cx="${x(p.date)}" cy="${y(p.value)}" r="4.5" fill="var(--surface)" stroke="${color}" stroke-width="2.5"
        data-tip="${`<b>${esc(s.name)}</b><br>${p.date}: ${Number(p.value).toFixed(1)}%${p.note ? "<br>" + esc(p.note) : ""}`}"/>`)}`;
  });
  return html`<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Score history line chart">
    <g class="axis">${ticks.map((t) => html`<line class="grid-line" x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}"/>
      <text x="${P.l - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`)}
      ${dates.filter((_, i) => i % step === 0).map((d) => html`<text x="${x(d)}" y="${H - 8}" text-anchor="middle">${new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" })}</text>`)}</g>
    ${thresholdLines(thresholds, P.l, W - P.r, y)}
    ${lines}</svg>
    ${series.length > 1 ? html`<div class="legend">${series.map((s, i) => html`<span><i style="background:${s.color || PALETTE[i % PALETTE.length]}"></i>${s.name}</span>`)}</div>` : ""}
  </div>`;
}

/** Vertical bar chart. items: [{label, value, color?, tip?}] */
export function barChart(items, { height = 240, thresholds = [], yMax = 100, colorFn } = {}) {
  if (!items.length) return html`<div class="empty">No data</div>`;
  const W = 720, H = height, P = { l: 40, r: 10, t: 14, b: 58 };
  const bw = (W - P.l - P.r) / items.length;
  const y = (v) => P.t + (1 - v / yMax) * (H - P.t - P.b);
  return html`<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart">
    <g class="axis">${[0, 25, 50, 75, 100].map((t) => html`<line class="grid-line" x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}"/>
      <text x="${P.l - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`)}</g>
    ${items.map((it, i) => {
      const v = it.value ?? 0, bx = P.l + i * bw + bw * 0.18, w = bw * 0.64;
      const color = it.color || (colorFn ? colorFn(v) : PALETTE[0]);
      const lbl = it.label.length > 14 ? it.label.slice(0, 13) + "…" : it.label;
      return html`<rect x="${bx}" y="${y(v)}" width="${w}" height="${Math.max(0, y(0) - y(v))}" rx="5" fill="${color}"
          data-tip="${it.tip || `<b>${esc(it.label)}</b><br>${Number(v).toFixed(1)}%`}"/>
        <text class="label" x="${bx + w / 2}" y="${y(v) - 5}" text-anchor="middle" font-weight="700">${Number(v).toFixed(0)}</text>
        <text class="label" transform="translate(${bx + w / 2},${H - P.b + 14}) rotate(-28)" text-anchor="end">${lbl}</text>`;
    })}
    ${thresholdLines(thresholds, P.l, W - P.r, y)}</svg></div>`;
}

/** Donut chart. items: [{label, value, color}] */
export function donut(items, { size = 170, centerLabel = "", centerValue = "" } = {}) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  const r = 62, c = 2 * Math.PI * r;
  let offset = 0;
  const arcs = items.filter((i) => i.value > 0).map((i) => {
    const len = (i.value / total) * c;
    const seg = html`<circle r="${r}" cx="85" cy="85" fill="none" stroke="${i.color}" stroke-width="22"
      stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 85 85)"
      data-tip="${`<b>${esc(i.label)}</b>: ${i.value}`}"/>`;
    offset += len;
    return seg;
  });
  return html`<div class="row" style="gap:20px;flex-wrap:nowrap">
    <svg viewBox="0 0 170 170" width="${size}" height="${size}" role="img" aria-label="Donut chart">
      <circle r="${r}" cx="85" cy="85" fill="none" stroke="var(--surface-2)" stroke-width="22"/>${arcs}
      <text x="85" y="84" text-anchor="middle" font-size="28" font-weight="800" fill="var(--text)">${centerValue}</text>
      <text x="85" y="104" text-anchor="middle" font-size="11" fill="var(--text-3)">${centerLabel}</text></svg>
    <div class="legend" style="flex-direction:column;gap:8px">${items.map((i) => html`<span><i style="background:${i.color}"></i>${i.label} <b>${i.value}</b></span>`)}</div>
  </div>`;
}

/** Tiny inline trend line. values: number[] */
export function sparkline(values, { width = 90, height = 26, color = "var(--primary)" } = {}) {
  if (!values || values.length < 2) return raw('<span class="subtle">—</span>');
  const min = Math.min(...values, 0), max = Math.max(...values, 100);
  const x = (i) => 2 + (i / (values.length - 1)) * (width - 4);
  const y = (v) => 2 + (1 - (v - min) / (max - min || 1)) * (height - 4);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return html`<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
    <path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${x(values.length - 1)}" cy="${y(values[values.length - 1])}" r="2.8" fill="${color}"/></svg>`;
}
