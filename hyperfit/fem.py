# SPDX-License-Identifier: GPL-3.0-or-later
"""FElupe adapter: independent AD tangents, mixed u/p/J finite elements."""
import numpy as np
import felupe as fem
import tensortrax.math as tm
from .models import Material
from .spectral import trace_power


def energy_function(material: Material):
    p = material.parameters.copy()
    def energy(c):
        j = tm.sqrt(tm.linalg.det(c))
        cb = c*j**(-2/3)
        i1 = tm.trace(cb)
        i2 = (i1**2-tm.trace(cb@cb))/2
        if material.deviatoric.startswith("ogden"):
            n = int(material.deviatoric[-1])
            wd = sum(2*p[f"mu{i}"]/p[f"alpha{i}"]**2 *
                     (trace_power(cb,p[f"alpha{i}"]/2)-3) for i in range(1,n+1))
        else:
            a,b = i1-3,i2-3
            wd = p["C10"]*a+p.get("C01",0)*b
            if material.deviatoric == "polynomial2":
                wd += p["C20"]*a*a+p["C11"]*a*b+p["C02"]*b*b
            if material.deviatoric == "yeoh":
                wd += p["C20"]*a*a+p["C30"]*a**3
        if material.volumetric == "quadratic_J":
            wv = p["K0"]*(j-1)**2/2
        elif material.volumetric == "polynomial2_J":
            wv = (j-1)**2/p["D1"]+(j-1)**4/p["D2"]
        else:
            t = tm.log(j)
            beta = p.get("beta",0)
            if beta == 0:
                wv = p["K0"]*t*t/2
            else:
                # tensortrax lacks expm1; stable hyperbolic identity, exact derivative.
                z = beta*t*t
                wv = p["K0"]/beta*tm.exp(z/2)*tm.sinh(z/2)
        return wd+wv
    return energy


def ad_material(material):
    return fem.Hyperelastic(energy_function(material))


def cube_test(material: Material, stretch=1.2, cells=2, steps=10, clamped=False,
              callback=None, cancel=None, element="hex8"):
    """Unit reference cube: roller tension or clamped right face with symmetry planes.

    Roller case is a homogeneous patch test, not a mesh-convergence proof.
    Clamped case is a distinct nonuniform benchmark (not the recovered specimen).
    """
    if not .7 <= stretch <= 1.7 or not 1 <= cells <= 8 or not 2 <= steps <= 100:
        raise ValueError("Benchmark range: stretch .7..1.7, cells 1..8, steps 2..100")
    mesh = fem.Cube(n=cells+1)
    if element=="hex8":
        region = fem.RegionHexahedron(mesh)
    elif element=="hex27":
        mesh=mesh.convert(order=2,calc_midfaces=True,calc_midvolumes=True)
        region=fem.RegionTriQuadraticHexahedron(mesh)
    else:
        raise ValueError("Use hex8 or hex27")
    field = fem.FieldsMixed(region, n=3)
    boundaries = fem.dof.uniaxial(field, clamped=clamped, return_loadcase=False)
    solid = fem.SolidBody(fem.ThreeFieldVariation(ad_material(material)), field)
    moves = np.linspace(0, stretch-1, steps+1)
    step = fem.Step(items=[solid], ramp={boundaries["move"]: moves}, boundaries=boundaries)
    records = []
    def capture(_step, substep, result):
        if cancel is not None and cancel.is_set():
            from .fitting import Cancelled
            raise Cancelled("Cancelled after a load increment")
        f = result.x[0].extract()
        j = fem.math.det(f)
        mixed_j=result.x[2].interpolate()[0]
        if np.any(j<=0) or np.any(mixed_j<=0):
            raise ValueError("Inverted element or nonpositive mixed volume")
        dv = region.dV
        mean_logj = float(np.sum(np.log(j)*dv)/np.sum(dv))
        records.append({"stretch": float(1+moves[substep]), "mean_log_J": mean_logj,
                        "min_J": float(j.min()), "max_J": float(j.max()),
                        "log_total_volume_ratio":float(np.log(np.sum(j*dv)/np.sum(dv))),
                        "mean_log_J_mixed":float(np.sum(np.log(mixed_j)*dv)/np.sum(dv)),
                        "max_J_constraint_gap":float(np.max(abs(j-mixed_j)))})
        if callback:callback({"increment":substep,"total_increments":steps})
    job = fem.CharacteristicCurve(steps=[step], boundary=boundaries["move"], callback=capture)
    job.evaluate(verbose=False, tol=1e-9, maxiter=40)
    forces = np.asarray(job.y)[:,0]
    for r, force in zip(records, forces):
        r["nominal_stress"] = float(force)  # reference area of unit cube is one
        if not clamped:
            r["cauchy_stress"] = float(force*r["stretch"]/np.exp(r["mean_log_J"]))
    return {"solver": f"FElupe {fem.__version__}", "formulation": "mixed u/p/J, "+("Hex8/P0/P0" if element=="hex8" else "Hex27/Q1d/Q1d"),
            "cells": cells**3, "clamped": clamped, "records": records,
            "description": "Unit cube verification, not the original specimen or Abaqus equivalence."}
