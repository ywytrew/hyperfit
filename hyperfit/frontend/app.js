// SPDX-License-Identifier: GPL-3.0-or-later
import { chart } from "./charts.js";
import { t, initializeLanguage, setLanguage, errorMessage } from "./i18n.js";
const $ = (id) => document.getElementById(id),
  API = window.HYPERFIT_API || "";
let catalog,
  data,
  result,
  chosen = 0,
  jobId,
  fitJobId,
  imported,
  filePayload,
  synthetic = true,
  pollTimer;
let status = { key: "status.ready", args: {} },
  errors = {},
  femResult;
function setStatus(key, args = {}) {
  status = { key, args };
  delete errors.progress;
  renderStatus();
}
function showError(target, error) {
  errors[target] = typeof error === "string" ? error : error.message;
  renderError(target);
}
function renderError(target) {
  const raw = errors[target];
  $(target + "-details").hidden = !raw;
  $(target + "-details").querySelector("pre").textContent = raw || "";
  if (raw) $(target).textContent = errorMessage(raw);
}
function renderStatus() {
  $("progress").textContent = t(status.key, status.args);
  renderError("progress");
}
function renderDataText() {
  if (!data) return;
  $("dataset").textContent = t(synthetic ? "data.synthetic" : "data.loaded", {
    name: data.name,
    count: data.log_strain.length,
  });
  $("curve-note").textContent = t(
    synthetic ? "response.synthetic" : "response.experimental",
  );
}
function renderImportText() {
  if (imported)
    $("import-summary").textContent = t("import.summary", {
      rows: imported.rows.length,
      columns: imported.headers.length,
    });
  renderError("import-error");
}
function renderFEM() {
  if (!femResult) {
    $("fem-result").textContent = "";
    return;
  }
  const r = femResult.records.at(-1);
  $("fem-result").textContent = t("fem.result", {
    cells: femResult.cells,
    stretch: r.stretch.toFixed(3),
    stress: r.cauchy_stress.toPrecision(6),
    volume: r.mean_log_J.toPrecision(6),
    stressError:
      femResult.analytic_comparison.max_nominal_stress_error.toExponential(2),
    volumeError: femResult.analytic_comparison.max_log_J_error.toExponential(2),
  });
}
function translateDynamic() {
  for (const id of ["dev", "vol"])
    for (const o of $(id).options) o.textContent = t("models." + o.value);
  document
    .querySelectorAll("[data-parameter]")
    .forEach((e) =>
      e.setAttribute(
        "aria-label",
        e.dataset.parameter + " " + t("param." + e.dataset.role),
      ),
    );
  $("mode-note").textContent = t("note." + $("mode").value);
  renderDataText();
  renderStatus();
  renderImportText();
  renderFEM();
  if (result) displayCandidates(chosen);
  else {
    $("count").textContent = t("candidate.none");
    draw();
  }
}
$("language").onchange = () => {
  setLanguage($("language").value);
  // Keep the URL consistent with the persisted preference after explicit switching.
  const url = new URL(location.href);
  url.searchParams.set("lang", $("language").value);
  history.replaceState(null, "", url);
  translateDynamic();
};
async function api(path, body) {
  const r = await fetch(
    API + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const j = await r.json();
  if (!r.ok)
    throw Error(
      typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail),
    );
  return j;
}
function option(select, value, label) {
  const o = document.createElement("option");
  o.value = value;
  o.textContent = label;
  select.append(o);
}
function resetResult() {
  result = null;
  fitJobId = null;
  $("export").disabled = true;
  $("candidates").hidden = true;
  $("selected-parameters").hidden = true;
  $("pareto-chart").hidden = true;
  $("candidate-empty").hidden = false;
  $("count").textContent = t("candidate.none");
  femResult = null;
  $("fem-result").textContent = "";
  draw();
}
function initParams() {
  const specs = {
    ...catalog.deviatoric[$("dev").value],
    ...catalog.volumetric[$("vol").value],
  };
  $("parameters").replaceChildren();
  for (const [name, s] of Object.entries(specs)) {
    const row = document.createElement("div");
    row.className = "param-row";
    const label = document.createElement("span");
    label.textContent = name;
    label.title = s.unit;
    row.append(label);
    for (const key of ["value", "lower", "upper"]) {
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = s[key];
      input.dataset.parameter = name;
      input.dataset.role = key;
      input.setAttribute("aria-label", `${name} ${t("param." + key)}`);
      row.append(input);
    }
    $("parameters").append(row);
  }
  $("formula").textContent =
    $("vol").value === "exponential_logJ"
      ? "W = Wdev + K₀ / (2β) · [exp(β · ln²J) − 1]"
      : "W = Wdev + Wvol(J)";
}
function material() {
  const parameters = {};
  document
    .querySelectorAll("[data-role=value]")
    .forEach((e) => (parameters[e.dataset.parameter] = Number(e.value)));
  return { deviatoric: $("dev").value, volumetric: $("vol").value, parameters };
}
function bounds() {
  const out = {};
  for (const e of document.querySelectorAll("[data-role=lower]"))
    out[e.dataset.parameter] = [
      Number(e.value),
      Number(
        document.querySelector(
          `[data-parameter="${e.dataset.parameter}"][data-role=upper]`,
        ).value,
      ),
    ];
  return out;
}
function showData() {
  renderDataText();
  resetResult();
}
function draw() {
  if (!data) return;
  const indices = data.log_strain
    .map((x, i) => i)
    .filter((i) => !$("zoom").checked || Math.abs(data.log_strain[i]) <= 0.1);
  const arr = (a) => indices.map((i) => a[i]);
  const p = result?.candidates[chosen]?.curves;
  for (const [key, id, title] of [
    ["stress", "stress-chart", t("chart.stress")],
    ["log_J", "volume-chart", t("chart.volume")],
  ]) {
    const series = [
      {
        x: arr(data.log_strain),
        y: arr(data[key]),
        color: "#91a0b1",
        name: t("response.observed"),
      },
    ];
    if (p)
      series.push({
        x: arr(p.log_strain),
        y: arr(p[key]),
        color: "#215ed4",
        line: true,
        name: t("response.predicted"),
      });
    chart(id, { title, series });
  }
  const rs = p
    ? ["stress", "log_J"].map((key, i) => ({
        x: arr(data.log_strain),
        y: arr(
          p[key].map(
            (v, n) =>
              (v - data[key][n]) / Math.max(...data[key].map(Math.abs), 1e-14),
          ),
        ),
        color: i ? "#d1924c" : "#215ed4",
        line: true,
        name: key,
      }))
    : [];
  chart("residual-chart", {
    title: t("chart.residual"),
    series: rs,
    zero: true,
  });
}
function selectCandidate(index) {
  chosen = index;
  const c = result.candidates[index];
  document
    .querySelectorAll("#candidates tbody tr")
    .forEach((tr, i) => tr.classList.toggle("selected", i === index));
  $("selected-parameters").hidden = false;
  $("selected-parameters").textContent =
    Object.entries(c.parameters)
      .map(([k, v]) => `${k} = ${v.toPrecision(7)}`)
      .join("    ") +
    (c.bound_hits.length
      ? `\n${t("candidate.boundHits", { names: c.bound_hits.join(", ") })}`
      : "");
  draw();
}
function displayCandidates(index = result.recommended_index) {
  const tbody = $("candidates").querySelector("tbody");
  tbody.replaceChildren();
  result.candidates.forEach((c, i) => {
    const tr = document.createElement("tr");
    const vals = [
      `${i + 1}${result.non_dominated_indices.includes(i) ? " · " + t("candidate.nondominated") : ""}`,
      c.metrics.stress.peak_nrmse?.toFixed(5) ?? "—",
      c.metrics.log_J.peak_nrmse?.toFixed(5) ?? "—",
      t(c.converged ? "candidate.converged" : "candidate.budget"),
      t(
        c.stability_screen?.positive_at_samples
          ? "candidate.stable"
          : "candidate.unstable",
      ),
      c.sensitivity_condition?.toExponential(2) ??
        t(
          c.sensitivity_diagnostic === "rank_deficient"
            ? "candidate.rankDeficient"
            : "candidate.unavailable",
        ),
    ];
    for (const val of vals) {
      const td = document.createElement("td");
      td.textContent = val;
      tr.append(td);
    }
    tr.addEventListener("click", () => selectCandidate(i));
    tr.tabIndex = 0;
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter") selectCandidate(i);
    });
    tbody.append(tr);
  });
  $("candidates").hidden = false;
  $("candidate-empty").hidden = true;
  $("count").textContent = t("candidate.count", {
    count: result.candidates.length,
    evaluations: result.evaluations,
  });
  $("pareto-chart").hidden = false;
  chart("pareto-chart", {
    title: t("chart.tradeoff"),
    xlabel: t("chart.tradeoffAxis"),
    scatter: true,
    onSelect: selectCandidate,
    series: [
      {
        x: result.candidates.map((c) => c.metrics.stress.rmse),
        y: result.candidates.map((c) => c.metrics.log_J.rmse),
        ids: result.candidates.map((_, i) => i),
        color: "#215ed4",
      },
    ],
  });
  selectCandidate(index);
}
function busy(on) {
  $("fit").disabled = on;
  $("fem").disabled = on;
  $("demo").disabled = on;
  $("file").disabled = on;
  $("dev").disabled = on;
  $("vol").disabled = on;
  $("cancel").hidden = !on;
}
async function poll(kind) {
  try {
    const s = await api(`/api/jobs/${jobId}`);
    if (s.status === "queued" || s.status === "running") {
      if (s.progress?.stage === "initialization")
        setStatus("status.sampling", {
          sampled: s.progress.sampled,
          total: s.progress.pool_size,
          valid: s.progress.valid_samples,
        });
      else if (s.progress?.evaluations)
        setStatus("status.fitting", {
          count: s.progress.evaluations,
          failed: s.progress.failed_evaluations,
        });
      else if (s.progress?.increment !== undefined)
        setStatus("status.increment", {
          step: s.progress.increment,
          total: s.progress.total_increments,
        });
      else setStatus("status.running");
      pollTimer = setTimeout(() => poll(kind), 900);
      return;
    }
    busy(false);
    if (s.status === "completed") {
      if (kind === "fit") {
        result = s.result;
        fitJobId = jobId;
        $("export").disabled = false;
        displayCandidates();
        setStatus(
          result.qualified_candidate_found
            ? "status.complete"
            : "status.unqualified",
        );
      } else {
        femResult = s.result;
        renderFEM();
        setStatus("status.femComplete");
      }
    } else if (s.error) showError("progress", s.error);
    else
      setStatus(
        s.status === "cancelled" ? "status.cancelled" : "status.interrupted",
      );
  } catch (e) {
    busy(false);
    showError("progress", e);
  }
}
$("fit").onclick = async () => {
  try {
    busy(true);
    setStatus("status.submitting");
    const mode = $("mode").value,
      uncertainty = mode === "uncertainty";
    const request = {
      material: material(),
      data,
      objective: {
        mode,
        stress_absolute: +$("sa").value,
        volume_absolute: +$("va").value,
        stress_relative: +$("relative").value,
        volume_relative: +$("relative").value,
        sampling: uncertainty ? "observations" : "strain_integral",
        low_strain_weight: uncertainty ? 1 : +$("lowweight").value,
      },
      starts: +$("starts").value,
      max_nfev: +$("budget").value,
      loss: $("loss").value,
      seed: +$("seed").value,
      initialization: $("initialization").value,
      pool_size: +$("poolsize").value,
      tradeoff: uncertainty ? false : $("tradeoff").checked,
      bounds: bounds(),
    };
    const r = await api("/api/fit", request);
    jobId = r.job_id;
    poll("fit");
  } catch (e) {
    busy(false);
    showError("progress", e);
  }
};
$("cancel").onclick = async () => {
  try {
    await api(`/api/jobs/${jobId}/cancel`, {});
    setStatus("status.cancelRequested");
  } catch (e) {
    showError("progress", e);
  }
};
$("fem").onclick = async () => {
  try {
    busy(true);
    setStatus("status.running");
    const m = result
      ? { ...result.model, parameters: result.candidates[chosen].parameters }
      : material();
    const r = await api("/api/fem", {
      material: m,
      stretch: 1.2,
      cells: 2,
      steps: 10,
      clamped: false,
    });
    jobId = r.job_id;
    poll("fem");
  } catch (e) {
    busy(false);
    showError("progress", e);
  }
};
$("export").onclick = () => {
  const a = document.createElement("a");
  a.href = `${API}/api/jobs/${fitJobId}/export?download=true&selected=${chosen}`;
  a.download = `hyperfit-${fitJobId}.json`;
  document.body.append(a);
  a.click();
  a.remove();
};
$("zoom").onchange = draw;
$("dev").onchange = $("vol").onchange = () => {
  initParams();
  resetResult();
};
$("mode").onchange = () => {
  if ($("mode").value === "uncertainty") $("loss").value = "linear";
  $("mode-note").textContent = t("note." + $("mode").value);
};
async function demo() {
  try {
    const d = await api("/api/demo");
    data = d.data;
    synthetic = true;
    showData();
  } catch (e) {
    showError("progress", e);
  }
}
$("demo").onclick = demo;
function mapping() {
  const mappingIds = ["strain-col", "stress-col", "volume-col"];
  mappingIds.forEach((id) => $(id).replaceChildren());
  imported.headers.forEach((h, i) =>
    mappingIds.forEach((id) => option($(id), i, h)),
  );
  $("stress-col").value = Math.max(
    0,
    imported.headers.findIndex((h) => /stress/i.test(h)),
  );
  $("volume-col").value = Math.max(
    0,
    imported.headers.findIndex((h) => /vol|log.?j/i.test(h)),
  );
  renderImportText();
}
$("file").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  try {
    const b = new Uint8Array(await f.arrayBuffer());
    let binary = "";
    for (let i = 0; i < b.length; i += 32768)
      binary += String.fromCharCode(...b.subarray(i, i + 32768));
    filePayload = { filename: f.name, content: btoa(binary) };
    imported = await api("/api/import", filePayload);
    $("sheet").replaceChildren();
    (imported.sheets.length ? imported.sheets : ["CSV"]).forEach((s) =>
      option($("sheet"), s, s),
    );
    $("sheet").disabled = !imported.sheets.length;
    mapping();
    delete errors["import-error"];
    $("import-error").textContent = "";
    renderError("import-error");
    $("import-dialog").showModal();
  } catch (e) {
    showError("progress", e);
  }
  e.target.value = "";
};
$("sheet").onchange = async () => {
  try {
    imported = await api("/api/import", {
      ...filePayload,
      sheet: $("sheet").value,
    });
    mapping();
  } catch (e) {
    showError("import-error", e);
  }
};
$("close-import").onclick = () => $("import-dialog").close();
$("mapping").onsubmit = async (e) => {
  e.preventDefault();
  try {
    data = await api("/api/normalize", {
      rows: imported.rows,
      strain_column: +$("strain-col").value,
      stress_column: +$("stress-col").value,
      volume_column: +$("volume-col").value,
      strain_measure: $("strain-measure").value,
      stress_measure: $("stress-measure").value,
      volume_measure: $("volume-measure").value,
      stress_unit: $("stress-unit").value,
      name: `${filePayload.filename} / ${$("sheet").value}`,
    });
    synthetic = false;
    $("import-dialog").close();
    showData();
  } catch (e) {
    showError("import-error", e);
  }
};
try {
  await initializeLanguage();
  translateDynamic();
  catalog = await api("/api/models");
  for (const k of Object.keys(catalog.deviatoric))
    option($("dev"), k, t("models." + k));
  for (const k of Object.keys(catalog.volumetric))
    option($("vol"), k, t("models." + k));
  $("dev").value = "mooney_rivlin";
  $("vol").value = "exponential_logJ";
  initParams();
  await demo();
} catch (e) {
  showError("progress", e);
}
