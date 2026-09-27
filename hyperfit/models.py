# SPDX-License-Identifier: GPL-3.0-or-later
"""Separable isotropic hyperelastic models with named parameters.

Reference-volume energy, J=det(F), Cauchy stress, Abaqus Ogden convention.
Analytic principal stress here is independent of the tensortrax FE derivatives.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Parameter:
    value: float
    lower: float
    upper: float
    logarithmic: bool = False
    unit: str = "MPa"


P = Parameter
DEVIATORIC = {
    "neo_hooke": {"C10": P(.5, .001, 10, True)},
    "mooney_rivlin": {"C10": P(.4, .001, 10, True), "C01": P(.15, .001, 10, True)},
    "polynomial2": {"C10": P(.4, -5, 10), "C01": P(.15, -5, 10),
                    "C20": P(.02, -5, 5), "C11": P(.01, -5, 5), "C02": P(.01, -5, 5)},
    "yeoh": {"C10": P(.5, .001, 10, True), "C20": P(.02, -5, 5), "C30": P(.005, 0, 5)},
}
for n in (1, 2, 3):
    parameters = {}
    for i in range(1, n + 1):
        parameters[f"mu{i}"] = P(1 / n, .001, 10, True)
        parameters[f"alpha{i}"] = P(2.0 if i % 2 else -2.0,
                                      .2 if i % 2 else -8, 8 if i % 2 else -.2,
                                      unit="1")
    DEVIATORIC[f"ogden{n}"] = parameters

VOLUMETRIC = {
    "quadratic_J": {"K0": P(100, .05, 10000, True)},
    "quadratic_logJ": {"K0": P(100, .05, 10000, True)},
    "exponential_logJ": {"K0": P(100, .05, 10000, True), "beta": P(1000, 0, 100000, unit="1")},
    "polynomial2_J": {"D1": P(.02, 1e-5, 40, True, "1/MPa"),
                       "D2": P(.05, 1e-5, 100, True, "1/MPa")},
}


def parameter_specs(dev: str, vol: str) -> dict[str, Parameter]:
    return {**DEVIATORIC[dev], **VOLUMETRIC[vol]}


@dataclass(frozen=True)
class Material:
    deviatoric: str
    volumetric: str
    parameters: dict[str, float]

    def __post_init__(self):
        specs = parameter_specs(self.deviatoric, self.volumetric)
        if set(self.parameters) != set(specs):
            raise ValueError(f"Expected named parameters: {', '.join(specs)}")
        if not all(np.isfinite(v) for v in self.parameters.values()):
            raise ValueError("Material parameters must be finite")
        p = self.parameters
        if self.shear_modulus <= 0:
            raise ValueError("Initial shear modulus must be positive")
        if any(p[k] <= 0 for k in ("K0", "D1", "D2") if k in p):
            raise ValueError("K0 and Di must be positive")
        if p.get("beta", 0) < 0:
            raise ValueError("This exponential model requires beta >= 0")
        if any(abs(v) < 1e-5 for k, v in p.items() if k.startswith("alpha")):
            raise ValueError("Ogden alpha too close to zero")

    @classmethod
    def default(cls, deviatoric="mooney_rivlin", volumetric="exponential_logJ"):
        return cls(deviatoric, volumetric,
                   {k: v.value for k, v in parameter_specs(deviatoric, volumetric).items()})

    @property
    def shear_modulus(self):
        p = self.parameters
        if self.deviatoric.startswith("ogden"):
            return sum(v for k, v in p.items() if k.startswith("mu"))
        return 2 * (p["C10"] + p.get("C01", 0))

    def volume(self, j):
        """Return W_vol, dW/dJ, d2W/dJ2. Overflow is an invalid state."""
        j = np.asarray(j, float)
        if np.any(j <= 0) or not np.all(np.isfinite(j)):
            raise ValueError("J must be finite and positive")
        p = self.parameters
        d = j - 1
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            if self.volumetric == "quadratic_J":
                return .5 * p["K0"] * d**2, p["K0"] * d, np.full_like(j, p["K0"])
            if self.volumetric == "polynomial2_J":
                return (d**2 / p["D1"] + d**4 / p["D2"],
                        2*d/p["D1"] + 4*d**3/p["D2"], 2/p["D1"] + 12*d**2/p["D2"])
            t = np.log(j)
            beta = p.get("beta", 0)
            factor = p["K0"] * np.exp(beta * t**2)
            w = .5*p["K0"]*t**2 if beta == 0 else p["K0"]*np.expm1(beta*t**2)/(2*beta)
            return w, factor*t/j, factor*(1-t+2*beta*t**2)/j**2

    def principal_cauchy(self, stretch):
        """Principal stretches on the last axis, return principal Cauchy stress."""
        l = np.asarray(stretch, float)
        if l.shape[-1] != 3 or np.any(l <= 0) or not np.all(np.isfinite(l)):
            raise ValueError("Three positive finite principal stretches required")
        j = np.prod(l, axis=-1)
        lb = l / j[..., None]**(1/3)
        p = self.parameters
        if self.deviatoric.startswith("ogden"):
            dev = np.zeros_like(l)
            for i in range(1, int(self.deviatoric[-1]) + 1):
                a = p[f"alpha{i}"]
                power = lb**a
                dev += 2*p[f"mu{i}"]/a * (power - power.mean(axis=-1, keepdims=True))
            dev /= j[..., None]
        else:
            b = lb**2
            i1, i2 = b.sum(axis=-1), (1/b).sum(axis=-1)
            w1 = np.full_like(j, p["C10"])
            w2 = np.full_like(j, p.get("C01", 0))
            if self.deviatoric == "polynomial2":
                w1 += 2*p["C20"]*(i1-3) + p["C11"]*(i2-3)
                w2 += p["C11"]*(i1-3) + 2*p["C02"]*(i2-3)
            elif self.deviatoric == "yeoh":
                w1 += 2*p["C20"]*(i1-3) + 3*p["C30"]*(i1-3)**2
            dev = 2/j[..., None] * (w1[..., None]*(b-i1[..., None]/3)
                                    - w2[..., None]*(1/b-i2[..., None]/3))
        return dev + self.volume(j)[1][..., None]


def uniaxial(material: Material, log_strain):
    """Homogeneous isotropic uniaxial response with traction-free lateral faces.

    Solve lateral stress=0 for log J; never impose incompressibility.
    Bracket is an explicit admissible log-volume interval, not a stability proof.
    """
    x = np.asarray(log_strain, float)
    if x.ndim != 1 or not np.all(np.isfinite(x)) or np.any(abs(x) > 2):
        raise ValueError("Expected a finite 1D logarithmic-strain array in [-2,2]")
    beta = material.parameters.get("beta", 0)
    limit = min(.5, np.sqrt(500/beta)) if beta > 0 else .5
    lo, hi = np.full_like(x, -limit), np.full_like(x, limit)

    def state(v):
        return np.exp(np.stack([x, (v-x)/2, (v-x)/2], axis=-1))

    if np.any(material.principal_cauchy(state(lo))[:, 1] >= 0) or np.any(material.principal_cauchy(state(hi))[:, 1] <= 0):
        raise ValueError("No bracketed traction-free solution in the admissible log-J interval")
    for _ in range(55):
        mid = (lo+hi)/2
        residual = material.principal_cauchy(state(mid))[:, 1]
        lo = np.where(residual < 0, mid, lo)
        hi = np.where(residual >= 0, mid, hi)
    v = (lo+hi)/2
    stretch = state(v)
    stress = material.principal_cauchy(stretch)
    if np.any(material.volume(np.exp(v))[2] <= 0):
        raise ValueError("Negative volumetric curvature on the solved path")
    if np.max(abs(stress[:, 1:]), initial=0) > 1e-6*max(1, np.max(abs(stress[:, 0]), initial=0)):
        raise ValueError("Lateral equilibrium tolerance not met")
    # Local monotonicity of the transverse equilibrium equation; not global material stability.
    h = 1e-7
    tangent = (material.principal_cauchy(state(v+h))[:, 1]
               - material.principal_cauchy(state(v-h))[:, 1])/(2*h)
    if np.any(tangent <= 0):
        raise ValueError("Non-positive transverse path tangent")
    return {"log_strain": x, "stress": stress[:, 0], "log_J": v,
            "nominal_stress": stress[:, 0]*np.exp(v-x), "stretch": stretch,
            "lateral_stress": stress[:, 1]}
