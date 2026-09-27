# SPDX-License-Identifier: GPL-3.0-or-later
"""Run inspectable FEM benchmarks: python -m hyperfit.verify --output PATH."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
from .models import Material,uniaxial
from .fem import cube_test
from .stability import acoustic_screen


def verify():
    m=Material("mooney_rivlin","exponential_logJ",dict(C10=.4642,C01=.434,K0=230,beta=34000))
    patch=[]
    for stretch in (.85,1.5):
        for cells in (1,2,3):
            fe=cube_test(m,stretch,cells,12)
            rows=fe["records"]
            mp=uniaxial(m,np.log([r["stretch"] for r in rows]))
            fe["max_nominal_stress_error"]=float(np.max(abs(np.array([r["nominal_stress"] for r in rows])-mp["nominal_stress"])))
            fe["max_log_J_error"]=float(np.max(abs(np.array([r["mean_log_J"] for r in rows])-mp["log_J"])))
            patch.append(fe)
    refinement=[]
    for cells in (2,3,4,6):
        fe=cube_test(m,1.3,cells,12,clamped=True)
        end=fe["records"][-1]
        refinement.append({"cells_per_axis":cells,"cells":cells**3,**end})
    force_changes=[abs(b["nominal_stress"]-a["nominal_stress"])/abs(b["nominal_stress"])
                   for a,b in zip(refinement[:-1],refinement[1:])]
    quadratic_refinement=[]
    for cells in (1,2,3,4):
        fe=cube_test(m,1.3,cells,12,clamped=True,element="hex27")
        quadratic_refinement.append({"cells_per_axis":cells,"cells":cells**3,**fe["records"][-1]})
    # Defined deformation domain, including actual traction-free uniaxial states
    # and prescribed determinant-one biaxial/planar/shear states.
    free=uniaxial(m,np.linspace(np.log(.8),np.log(1.65),11))
    fs=[np.diag(l) for l in free["stretch"]]
    labels=[f"free_uniaxial_{i}" for i in range(len(fs))]
    for l in (.8,1.2,1.5):
        fs += [np.diag([l,l,l**-2]),np.diag([l,1,l**-1])]
        labels += [f"isochoric_biaxial_{l}",f"isochoric_planar_{l}"]
    for g in (.2,.5,.8):
        fs.append(np.array([[1,g,0],[0,1,0],[0,0,1.]]));labels.append(f"simple_shear_{g}")
    for j in (.997,1.003):
        fs.append(np.eye(3)*j**(1/3));labels.append(f"hydrostatic_J_{j}")
    screen=acoustic_screen(m,np.array(fs),directions=200)
    screen["state_labels"]=labels
    return {"created_at":datetime.now(timezone.utc).isoformat(),"material":asdict(m),
            "patch_tests":patch,"clamped_refinement":refinement,
            "clamped_quadratic_refinement":quadratic_refinement,
            "relative_force_change_between_meshes":force_changes,
            "refinement_note":"Successive mesh differences are observations, not a certified error bound. Check reaction AND volume observables. The mixed J field and det(F) agree only weakly; report their gap. Mean(log J) differs from log(mean J) in a nonuniform body. Clamped cube is not the original specimen.",
            "sampled_stability":screen,"abaqus_verified":False}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",default="validation-results/fem-verification.json")
    args=p.parse_args();result=verify()
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({"output":str(path),"maximum_patch_stress_error":max(r["max_nominal_stress_error"] for r in result["patch_tests"]),
                      "maximum_patch_log_J_error":max(r["max_log_J_error"] for r in result["patch_tests"]),
                      "mesh_force_changes":result["relative_force_change_between_meshes"],
                      "sampled_acoustic_minimum":result["sampled_stability"]["minimum_eigenvalue"]},indent=2))
