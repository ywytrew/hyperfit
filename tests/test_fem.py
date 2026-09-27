# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
import pytest
from numpy.testing import assert_allclose
from hyperfit.models import Material,uniaxial
from hyperfit.fem import cube_test


@pytest.mark.parametrize("stretch",[.85,1.25])
@pytest.mark.parametrize("cells",[1,2])
def test_mixed_cube_paper_material_matches_analytic(stretch,cells):
    m=Material("mooney_rivlin","exponential_logJ",dict(C10=.4642,C01=.434,K0=230,beta=34000))
    result=cube_test(m,stretch=stretch,cells=cells,steps=6)
    records=result["records"]
    p=uniaxial(m,np.log([r["stretch"] for r in records]))
    assert_allclose([r["nominal_stress"] for r in records],p["nominal_stress"],atol=2e-8,rtol=2e-7)
    assert_allclose([r["mean_log_J"] for r in records],p["log_J"],atol=2e-10,rtol=2e-7)


def test_nearly_incompressible_mixed_cube():
    m=Material("neo_hooke","quadratic_J",dict(C10=.5,K0=10000))
    result=cube_test(m,stretch=1.2,cells=2,steps=6)
    r=result["records"][-1];p=uniaxial(m,np.log([1.2]))
    assert_allclose(r["nominal_stress"],p["nominal_stress"][0],rtol=2e-6)
    assert_allclose(r["mean_log_J"],p["log_J"][0],rtol=2e-6,atol=1e-10)


@pytest.mark.parametrize("dev",["ogden1","ogden2","ogden3"])
def test_ogden_mixed_cube_repeated_eigenvalues(dev):
    m=Material.default(dev)
    r=cube_test(m,stretch=1.2,cells=2,steps=6)["records"][-1]
    p=uniaxial(m,np.log([1.2]))
    assert_allclose(r["nominal_stress"],p["nominal_stress"][0],rtol=2e-7)
    assert_allclose(r["mean_log_J"],p["log_J"][0],atol=2e-10)


def test_quadratic_mixed_cube_and_volume_observables():
    m=Material.default()
    r=cube_test(m,stretch=1.2,cells=2,steps=6,element="hex27")["records"][-1]
    p=uniaxial(m,np.log([1.2]))
    assert_allclose(r["nominal_stress"],p["nominal_stress"][0],rtol=2e-7)
    for key in ("mean_log_J","mean_log_J_mixed","log_total_volume_ratio"):
        assert_allclose(r[key],p["log_J"][0],atol=2e-10)
    assert r["max_J_constraint_gap"]<1e-9
