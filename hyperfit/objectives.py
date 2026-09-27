# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit residual definitions. Tolerances are not measurement uncertainties."""
from dataclasses import dataclass
import numpy as np


@dataclass
class Dataset:
    log_strain: np.ndarray
    stress: np.ndarray
    log_J: np.ndarray
    name: str = "experiment"

    def __post_init__(self):
        for key in ("log_strain", "stress", "log_J"):
            setattr(self, key, np.asarray(getattr(self, key), float))
        if self.log_strain.ndim != 1:
            raise ValueError("Observations must be one-dimensional")
        n = len(self.log_strain)
        if n < 4 or any(v.ndim != 1 or len(v) != n or not np.all(np.isfinite(v))
                        for v in (self.log_strain, self.stress, self.log_J)):
            raise ValueError("At least four aligned finite observations are required")
        if np.any(np.diff(self.log_strain) <= 0):
            raise ValueError("Select a single monotonic branch; strain must be strictly increasing")

    def payload(self):
        return {"name": self.name, **{k: getattr(self, k).tolist() for k in ("log_strain", "stress", "log_J")}}


@dataclass
class Objective:
    mode: str = "tolerance"
    stress_absolute: float = .02
    stress_relative: float = .02
    volume_absolute: float = .0002
    volume_relative: float = .02
    sampling: str = "strain_integral"
    low_strain_limit: float = .1
    low_strain_weight: float = 1.0
    stress_importance: float = 1.0
    volume_importance: float = 1.0

    def __post_init__(self):
        if self.mode not in ("tolerance", "uncertainty", "peak"):
            raise ValueError("Unknown normalization mode")
        if self.sampling not in ("strain_integral", "observations"):
            raise ValueError("Unknown sampling measure")
        if self.mode == "uncertainty" and (self.sampling != "observations" or self.low_strain_weight != 1):
            raise ValueError("Uncertainty mode uses independent observations without preference weights")
        vals = [self.stress_absolute, self.volume_absolute, self.low_strain_weight,
                self.stress_importance, self.volume_importance]
        if any(not np.isfinite(v) or v <= 0 for v in vals):
            raise ValueError("Absolute scales and weights must be positive and finite")
        if any(not np.isfinite(v) or v < 0 for v in [self.stress_relative, self.volume_relative]):
            raise ValueError("Relative scales must be finite and nonnegative")
        if not np.isfinite(self.low_strain_limit) or self.low_strain_limit < 0:
            raise ValueError("Low-strain limit must be finite and nonnegative")

    def weights(self, data):
        x = data.log_strain
        if self.sampling == "observations":
            w = np.ones(len(x))
        else:
            dx = np.diff(x)
            w = np.r_[dx[0]/2, (dx[:-1]+dx[1:])/2, dx[-1]/2]
        w *= np.where(abs(x) <= self.low_strain_limit, self.low_strain_weight, 1)
        # Preserve likelihood sample count for known independent uncertainties.
        return w if self.mode == "uncertainty" else w / w.sum()

    def residuals(self, data, prediction, loss="linear"):
        """sqrt(weight) * signed sqrt(rho(error/scale)).

        Robustification precedes quadrature weighting: the tolerance threshold
        must not grow when a curve is sampled more densely. Feed this residual
        to least_squares(loss='linear'); do not robustify it a second time.
        """
        if loss not in ("linear", "soft_l1", "huber"):
            raise ValueError("Unknown robust loss")
        output = []
        for key, absolute, relative, importance in (
                ("stress", self.stress_absolute, self.stress_relative, self.stress_importance),
                ("log_J", self.volume_absolute, self.volume_relative, self.volume_importance)):
            y = getattr(data, key)
            if self.mode == "peak":
                scale = np.max(np.abs(y))
                if scale <= 1e-14:
                    raise ValueError("Peak normalization undefined for a zero signal; use absolute tolerance")
            else:
                scale = np.hypot(absolute, relative*abs(y))
            r = (prediction[key]-y)/scale
            if loss == "soft_l1":
                r = r*np.sqrt(2/(np.hypot(1,r)+1))
            elif loss == "huber":
                r = np.sign(r)*np.sqrt(np.where(abs(r)<=1,r*r,2*abs(r)-1))
            output.append(np.sqrt(importance*self.weights(data))*r)
        return np.concatenate(output)


def metrics(data, prediction):
    result = {}
    for key in ("stress", "log_J"):
        y = getattr(data, key)
        err = prediction[key]-y
        peak = np.max(abs(y))
        low = abs(data.log_strain) <= .1
        result[key] = {"rmse": float(np.sqrt(np.mean(err**2))),
                       "peak_nrmse": float(np.sqrt(np.mean(err**2))/peak) if peak > 1e-14 else None,
                       "max_absolute_error": float(np.max(abs(err))),
                       "low_strain_rmse": float(np.sqrt(np.mean(err[low]**2))) if low.any() else None}
    return result


def non_dominated(values):
    """Indices of finite non-dominated candidates, not a global Pareto-front claim."""
    a = np.asarray(values, float)
    valid = np.all(np.isfinite(a), axis=1)
    return [i for i in range(len(a)) if valid[i] and not any(
        valid[j] and np.all(a[j] <= a[i]) and np.any(a[j] < a[i]) for j in range(len(a)) if i != j)]
