// SPDX-License-Identifier: GPL-3.0-or-later
const dictionaries = {};
export const languages = ["zh", "en", "ja"];
let current = "zh";
export function locale() {
  return current;
}
export function t(key, values = {}) {
  const text = dictionaries[current]?.[key] ?? dictionaries.zh?.[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
}
export async function initializeLanguage() {
  await Promise.all(
    languages.map(async (lang) => {
      const response = await fetch(
        new URL(`./locales/${lang}.json`, import.meta.url),
      );
      if (!response.ok) throw Error(`Cannot load locale: ${lang}`);
      dictionaries[lang] = await response.json();
    }),
  );
  let saved;
  try {
    saved = localStorage.getItem("hyperfit.language");
  } catch {}
  setLanguage(
    new URLSearchParams(location.search).get("lang") || saved || "zh",
  );
}
export function setLanguage(lang) {
  current = languages.includes(lang) ? lang : "zh";
  try {
    localStorage.setItem("hyperfit.language", current);
  } catch {}
  document.documentElement.lang = { zh: "zh-CN", en: "en", ja: "ja" }[current];
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.getElementById("language").value = current;
  document.getElementById("manual").href = `manual-${current}.html`;
}
export function errorMessage(raw) {
  let match = raw.match(/Only (\d+) valid initial points for (\d+) starts/);
  if (match) return t("error.pool", { valid: match[1], starts: match[2] });
  match = raw.match(/Expected named parameters: (.*)/);
  if (match) return t("error.expectedParams", { names: match[1] });
  const rules = [
    [/fetch|network|Failed to fetch/i, "network"],
    [/strictly increasing|monotonic branch/i, "monotonic"],
    [/four aligned|one-dimensional|4.?3000 points/, "points"],
    [/Initial parameters must lie/, "initial"],
    [/Seed must/, "seed"],
    [/Invalid parameter bounds|Bounds require/, "bounds"],
    [/bounded\/manual|initialization|pool of starts/, "initialization"],
    [/1\.\.10 starts|5\.\.500 evaluations/, "budget"],
    [
      /Material parameters|Initial shear|K0 and Di|beta >=|Ogden alpha|alpha interval/,
      "physical",
    ],
    [/scales.*finite|weights must|Low-strain limit/, "scales"],
    [/Uncertainty mode|Likelihood mode/, "uncertainty"],
    [/zero signal/, "zeroPeak"],
    [/No valid candidate/, "noCandidate"],
    [
      /principal stretches|logarithmic-strain|traction-free|volumetric curvature|Lateral equilibrium|transverse path|Inverted element|J must/,
      "forward",
    ],
    [/10 MB/, "fileSize"],
    [/50000 rows|Too many rows/, "rows"],
    [/Use .csv|legacy .xls/, "fileType"],
    [/table header/, "header"],
    [/Column indices|distinct observation columns/, "columns"],
    [/blanks|non-numeric|Non-finite observation/, "cells"],
    [
      /strain measure|volume measure|stress is accepted|stress unit/,
      "measures",
    ],
    [/has not completed/, "notComplete"],
    [/Not Found/, "notFound"],
    [/Invalid selected candidate/, "selection"],
    [
      /"loc"|Unknown normalization|Unknown robust|Unsupported robust|Unknown sampling/,
      "validation",
    ],
  ];
  const rule = rules.find(([pattern]) => pattern.test(raw));
  return t(`error.${rule?.[1] || "generic"}`);
}
