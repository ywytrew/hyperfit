// SPDX-License-Identifier: GPL-3.0-or-later
import { t } from "./i18n.js";
const NS = "http://www.w3.org/2000/svg";
function el(type, attrs = {}, text) {
  const n = document.createElementNS(NS, type);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  return n;
}
const fmt = (v) =>
  Math.abs(v) >= 1e4 || (Math.abs(v) > 0 && Math.abs(v) < 0.001)
    ? v.toExponential(1)
    : Number(v.toPrecision(3)).toString();
export function chart(
  target,
  {
    title = "",
    xlabel = t("chart.strain"),
    series = [],
    scatter = false,
    onSelect = null,
    zero = false,
  },
) {
  const root = document.getElementById(target);
  root.replaceChildren();
  const W = 690,
    H = scatter ? 185 : target === "residual-chart" ? 185 : 242,
    L = 58,
    R = 20,
    T = 38,
    B = 38;
  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": title,
  });
  root.append(svg);
  const points = series.flatMap((s) =>
    s.x.map((x, i) => [x, s.y[i]]).filter((p) => p.every(Number.isFinite)),
  );
  svg.append(el("text", { x: 4, y: 17, class: "title" }, title));
  if (!points.length) {
    svg.append(
      el(
        "text",
        { x: W / 2, y: H / 2, "text-anchor": "middle" },
        t("chart.empty"),
      ),
    );
    return;
  }
  let xmin = Math.min(...points.map((p) => p[0])),
    xmax = Math.max(...points.map((p) => p[0])),
    ymin = Math.min(...points.map((p) => p[1])),
    ymax = Math.max(...points.map((p) => p[1]));
  if (zero) {
    ymin = Math.min(0, ymin);
    ymax = Math.max(0, ymax);
  }
  if (xmin === xmax) {
    xmin -= 0.01;
    xmax += 0.01;
  }
  if (ymin === ymax) {
    ymin -= 0.01;
    ymax += 0.01;
  }
  const pad = (ymax - ymin) * 0.1;
  ymin -= pad;
  ymax += pad;
  const px = (x) => L + ((x - xmin) / (xmax - xmin)) * (W - L - R),
    py = (y) => H - B - ((y - ymin) / (ymax - ymin)) * (H - T - B);
  for (let i = 0; i <= 4; i++) {
    const y = ymin + ((ymax - ymin) * i) / 4,
      x = xmin + ((xmax - xmin) * i) / 4;
    svg.append(
      el("line", { x1: L, x2: W - R, y1: py(y), y2: py(y), stroke: "#eaf0f5" }),
      el("text", { x: L - 10, y: py(y) + 3, "text-anchor": "end" }, fmt(y)),
      el("text", { x: px(x), y: H - B + 19, "text-anchor": "middle" }, fmt(x)),
    );
  }
  svg.append(
    el("text", { x: (W + L) / 2, y: H - 2, "text-anchor": "middle" }, xlabel),
  );
  if (zero && ymin < 0 && ymax > 0)
    svg.append(
      el("line", {
        x1: L,
        x2: W - R,
        y1: py(0),
        y2: py(0),
        stroke: "#a4b4c3",
        "stroke-dasharray": "4 4",
      }),
    );
  for (const s of series) {
    if (s.line) {
      let d = "";
      s.x.forEach((x, i) => {
        if (Number.isFinite(s.y[i]))
          d += `${d ? "L" : "M"}${px(x)},${py(s.y[i])} `;
      });
      svg.append(
        el("path", { d, fill: "none", stroke: s.color, "stroke-width": 2 }),
      );
    } else
      s.x.forEach((x, i) => {
        if (!Number.isFinite(s.y[i])) return;
        const dot = el("circle", {
          cx: px(x),
          cy: py(s.y[i]),
          r: scatter ? 6 : 2.6,
          fill: s.color,
          opacity: scatter ? 1 : 0.75,
          tabindex: scatter ? 0 : -1,
        });
        dot.append(
          el("title", {}, `${s.name || ""} ${fmt(x)}, ${fmt(s.y[i])}`),
        );
        if (scatter && onSelect) {
          dot.style.cursor = "pointer";
          dot.addEventListener("click", () => onSelect(s.ids[i]));
          dot.addEventListener("keydown", (e) => {
            if (e.key === "Enter") onSelect(s.ids[i]);
          });
        }
        svg.append(dot);
      });
  }
}
