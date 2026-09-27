# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite directional strong-ellipticity screen, never a global stability proof."""
import numpy as np
from .fem import ad_material


def acoustic_screen(material, gradients, directions=80, seed=7):
    """Sample Q_ik=A_iJkL n_J n_L, A=dP/dF (reference description).

    A nonpositive eigenvalue finds a loss of strong ellipticity at the sampled
    state/direction. Positive samples do not certify unsampled states/directions,
    global energy convexity, structural stability or Newton convergence.
    """
    gradients = np.asarray(gradients, float)
    if gradients.ndim != 3 or gradients.shape[1:] != (3,3):
        raise ValueError("Expected N deformation gradients of shape 3x3")
    if np.any(np.linalg.det(gradients) <= 0):
        raise ValueError("Positive determinant required")
    rng = np.random.default_rng(seed)
    n = np.vstack([np.eye(3),rng.normal(size=(directions,3))])
    n /= np.linalg.norm(n,axis=1)[:,None]
    umat = ad_material(material)
    minima=[]
    worst_direction=[]
    for f in gradients:
        a = umat.hessian([f[:,:,None,None]])[0][...,0,0]
        q = np.einsum("ijkl,dj,dl->dik",a,n,n)
        eig = np.linalg.eigvalsh((q+q.swapaxes(1,2))/2)[:,0]
        idx = int(np.argmin(eig))
        minima.append(float(eig[idx])); worst_direction.append(n[idx].tolist())
    index = int(np.argmin(minima))
    return {"minimum_eigenvalue":minima[index], "minimum_by_state":minima,
            "positive_at_samples":bool(minima[index]>0), "worst_state_index":index,
            "worst_direction":worst_direction[index], "directions_per_state":len(n),
            "gradients":gradients.tolist(), "seed":seed, "units":"MPa",
            "scope":"Sampled rank-one tangent check only; not a global stability certificate."}
