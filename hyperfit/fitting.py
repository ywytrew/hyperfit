# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, scaled multi-start calibration; candidate comparison remains explicit."""
from dataclasses import asdict
from threading import Event
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import qmc
from .models import Material, parameter_specs, uniaxial
from .objectives import Dataset, Objective, metrics, non_dominated
from .stability import acoustic_screen


class Cancelled(Exception):
    pass


def fit(data: Dataset, initial: Material, objective: Objective, starts=3, max_nfev=100,
        loss="soft_l1", seed=42, bounds=None, callback=None, cancel: Event | None = None,
        tradeoff=False, initialization="bounded", pool_size=48):
    if loss not in ("linear", "soft_l1", "huber"):
        raise ValueError("Unsupported robust loss")
    if not 1 <= starts <= 10 or not 5 <= max_nfev <= 500:
        raise ValueError("Use 1..10 starts and 5..500 evaluations per start")
    if initialization not in ("bounded","manual") or not starts <= pool_size <= 256:
        raise ValueError("Use bounded/manual initialization and a pool of starts..256 points")
    if not isinstance(seed,(int,np.integer)) or not 0 <= seed <= 2**32-1:
        raise ValueError("Seed must be an integer in 0..4294967295")
    if objective.mode == "uncertainty" and (objective.stress_importance != 1 or objective.volume_importance != 1 or tradeoff):
        raise ValueError("Likelihood mode does not mix researcher preference weights")
    specs = parameter_specs(initial.deviatoric, initial.volumetric)
    names = list(specs)
    if bounds and (set(bounds)-set(names) or any(len(v)!=2 for v in bounds.values())):
        raise ValueError("Bounds require two endpoints for known parameter names")
    lower = np.array([bounds[k][0] if bounds and k in bounds else specs[k].lower for k in names], float)
    upper = np.array([bounds[k][1] if bounds and k in bounds else specs[k].upper for k in names], float)
    logs = np.array([specs[k].logarithmic for k in names])
    if np.any(lower >= upper) or not np.all(np.isfinite([lower, upper])) or np.any(lower[logs] <= 0):
        raise ValueError("Invalid parameter bounds")
    for i,k in enumerate(names):
        if (k.startswith("alpha") and lower[i]<=0<=upper[i]) or (k=="beta" and lower[i]<0):
            raise ValueError("Keep each Ogden alpha interval away from zero, and beta >= 0")
    def transform(a):
        b = a.copy(); b[logs] = np.log(b[logs]); return b
    lo, hi = transform(lower), transform(upper)
    def decode(z):
        p = lo+z*(hi-lo); p[logs] = np.exp(p[logs])
        return Material(initial.deviatoric, initial.volumetric, dict(zip(names, p)))
    first = (transform(np.array([initial.parameters[k] for k in names]))-lo)/(hi-lo)
    if initialization=="manual" and (np.any(first < 0) or np.any(first > 1)):
        raise ValueError("Initial parameters must lie within selected bounds")
    rng = np.random.default_rng(seed)
    evaluations = 0
    failures = 0
    candidates = []
    initialization_records=[]
    rejected={}
    if initialization=="bounded":
        # Latin hypercube covers every transformed parameter interval instead of
        # perturbing a hand-entered guess. Coupled forward solves screen the pool.
        points=qmc.LatinHypercube(d=len(names),seed=seed).random(pool_size)
        accepted=[]
        for idx,z in enumerate(points):
            if cancel is not None and cancel.is_set():raise Cancelled("Cancelled during initialization")
            try:
                m=decode(z);p=uniaxial(m,data.log_strain)
                r=objective.residuals(data,p,loss)
                score=float(.5*np.dot(r,r))
                if not np.isfinite(score):raise ValueError("Non-finite initialization score")
                accepted.append((score,idx,z))
                initialization_records.append({"sample":idx,"parameters":m.parameters,"cost":score,"valid":True})
            except (ValueError,FloatingPointError,OverflowError) as exc:
                reason=str(exc)
                rejected[reason]=rejected.get(reason,0)+1
                initialization_records.append({"sample":idx,"valid":False,"reason":reason})
            if callback and ((idx+1)%8==0 or idx+1==pool_size):
                callback({"stage":"initialization","sampled":idx+1,"pool_size":pool_size,"valid_samples":len(accepted)})
        accepted.sort(key=lambda t:t[0])
        if len(accepted)<starts:
            raise ValueError(f"Only {len(accepted)} valid initial points for {starts} starts. Adjust physical bounds or increase the pool.")
        selected=[]
        for item in accepted:
            if not selected or min(np.linalg.norm(item[2]-v[2])/np.sqrt(len(names)) for v in selected)>=.15:
                selected.append(item)
            if len(selected)==starts:break
        for item in accepted:
            if len(selected)==starts:break
            if all(item[1]!=v[1] for v in selected):selected.append(item)
        starting_points=[v[2] for v in selected]
        selected_samples=[v[1] for v in selected]
    else:
        starting_points=[first]+[np.clip(first+rng.normal(0,.10,len(names)),.001,.999) for _ in range(starts-1)]
        selected_samples=[]
    # A small weight sweep is labelled an explored tradeoff, not NSGA-II/global Pareto.
    ratios = (0.1, 1.0, 10.0) if tradeoff else (1.0,)
    for ratio in ratios:
        config = asdict(objective)
        config["volume_importance"] *= ratio
        active = Objective(**config)
        for start in range(starts):
            z0 = starting_points[start]
            def residual(z):
                nonlocal evaluations, failures
                if cancel is not None and cancel.is_set():
                    raise Cancelled("Cancelled by user")
                evaluations += 1
                try:
                    prediction = uniaxial(decode(z), data.log_strain)
                    r = active.residuals(data, prediction, loss)
                    if not np.all(np.isfinite(r)): raise ValueError("Non-finite residual")
                except (ValueError, FloatingPointError, OverflowError):
                    failures += 1
                    # Fixed vector length; failed endpoints are never accepted as candidates.
                    r = np.full(2*len(data.log_strain), 1e6)
                if callback and evaluations % 10 == 0:
                    callback({"evaluations": evaluations, "failed_evaluations": failures,
                              "start": start+1, "volume_weight_ratio": ratio})
                return r
            result = least_squares(residual, z0, bounds=(np.zeros(len(names)), np.ones(len(names))),
                                   method="trf", loss="linear",
                                   max_nfev=max_nfev, xtol=1e-8, ftol=1e-8, gtol=1e-8)
            try:
                material = decode(result.x)
                prediction = uniaxial(material, data.log_strain)
            except (ValueError, FloatingPointError, OverflowError):
                continue
            raw = active.residuals(data, prediction)
            # Diagnose raw scaled residual sensitivity, not robust-weighted optimizer Jacobian.
            condition, diagnostic = None, "ok"
            try:
                jac = np.empty((len(raw), len(names)))
                for i in range(len(names)):
                    delta = np.zeros(len(names)); delta[i] = 1e-5
                    zp = np.minimum(1, result.x+delta); zm = np.maximum(0, result.x-delta)
                    jac[:, i] = (active.residuals(data, uniaxial(decode(zp), data.log_strain))
                                 - active.residuals(data, uniaxial(decode(zm), data.log_strain)))/(zp[i]-zm[i])
                sv = np.linalg.svd(jac, compute_uv=False)
                if sv[-1] > 1e-14:
                    condition = float(sv[0]/sv[-1])
                else:
                    diagnostic = "rank_deficient"
            except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
                diagnostic = "unavailable_at_parameter_boundary"
            sample_indices=np.unique(np.linspace(0,len(data.log_strain)-1,min(11,len(data.log_strain))).astype(int))
            try:
                screen=acoustic_screen(material,np.array([np.diag(prediction["stretch"][i]) for i in sample_indices]))
            except (ValueError,FloatingPointError,OverflowError,np.linalg.LinAlgError) as exc:
                screen={"positive_at_samples":False,"error":str(exc),"scope":"Screen unavailable"}
            candidates.append({"parameters": material.parameters, "metrics": metrics(data, prediction),
                               "curves": {k: prediction[k].tolist() for k in ("log_strain", "stress", "log_J")},
                               "loss_cost": float(result.cost), "converged": bool(result.success),
                               "message": result.message, "weight_ratio": ratio,
                               "initial_parameters":decode(z0).parameters,
                               "sensitivity_condition": condition,
                               "sensitivity_diagnostic": diagnostic,
                               "stability_screen":screen,
                               "selection_eligible":bool(result.success and screen["positive_at_samples"]),
                               "bound_hits": [names[i] for i,z in enumerate(result.x) if min(z,1-z)<1e-4]})
    if not candidates:
        raise ValueError("No valid candidate found; check model, parameter bounds and data definitions")
    # Re-score all candidates under the same objective for cross-weight comparison.
    for c in candidates:
        r = objective.residuals(data, {k: np.asarray(v) for k,v in c["curves"].items()}, loss)
        c["comparison_cost"] = float(.5*np.dot(r,r))
    eligible=[i for i,c in enumerate(candidates) if c["selection_eligible"]]
    best = min(eligible or range(len(candidates)), key=lambda i: candidates[i]["comparison_cost"])
    nd = non_dominated([[c["metrics"][k]["rmse"] for k in ("stress", "log_J")] for c in candidates])
    return {"candidates": candidates, "recommended_index": best, "non_dominated_indices": nd,
            "evaluations": evaluations, "failed_evaluations": failures,
            "solver": "homogeneous_material_point", "objective": asdict(objective), "loss": loss,
            "seed": seed, "model": {"deviatoric": initial.deviatoric, "volumetric": initial.volumetric},
            "initialization":{"method":initialization,"seed":seed,"pool_size":pool_size if initialization=="bounded" else 0,
                              "sample_records":initialization_records,"selected_samples":selected_samples,
                              "starting_parameters":[decode(z).parameters for z in starting_points],
                              "rejection_reasons":rejected,"screen_scope":"Coupled uniaxial equilibrium and local path checks; not global stability.",
                              "bounds":{k:[float(lower[i]),float(upper[i])] for i,k in enumerate(names)}},
            "qualified_candidate_found":bool(eligible),
            "selection_note": ("Minimum common objective among converged candidates with positive sampled acoustic tensors."
                               if eligible else "No qualified candidate. Displayed minimum is diagnostic only.")+
                              " Not proof of global stability, uniqueness or global optimality."}
