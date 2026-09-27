# SPDX-License-Identifier: GPL-3.0-or-later
from threading import Event
import numpy as np
import pytest
from numpy.testing import assert_allclose
from hyperfit.models import Material,uniaxial
from hyperfit.objectives import Dataset,Objective
from hyperfit.fitting import fit,Cancelled


def test_recover_known_parameters_and_predict_unseen_strains():
    truth=Material("mooney_rivlin","exponential_logJ",dict(C10=.4642,C01=.434,K0=230,beta=34000))
    train=uniaxial(truth,np.linspace(0,.48,25))
    data=Dataset(train["log_strain"],train["stress"],train["log_J"])
    initial=Material("mooney_rivlin","exponential_logJ",dict(C10=.4,C01=.3,K0=200,beta=20000))
    result=fit(data,initial,Objective(),starts=1,max_nfev=100,loss="linear",initialization="manual")
    c=result["candidates"][result["recommended_index"]]
    assert c["converged"]
    for k,v in truth.parameters.items():assert_allclose(c["parameters"][k],v,rtol=2e-4)
    recovered=Material(truth.deviatoric,truth.volumetric,c["parameters"])
    x=np.array([-.12,.071,.223,.511])
    for key in ("stress","log_J"):
        assert_allclose(uniaxial(recovered,x)[key],uniaxial(truth,x)[key],rtol=3e-4,atol=1e-8)


def test_cancellation_is_not_a_failed_candidate():
    p=uniaxial(Material.default(),np.linspace(0,.3,8))
    d=Dataset(p["log_strain"],p["stress"],p["log_J"])
    e=Event();e.set()
    with pytest.raises(Cancelled):fit(d,Material.default(),Objective(),cancel=e)


def test_bounded_random_initialization_is_reproducible_and_ignores_manual_guess():
    truth=Material("neo_hooke","quadratic_J",dict(C10=.72,K0=180))
    p=uniaxial(truth,np.linspace(0,.4,13));d=Dataset(p["log_strain"],p["stress"],p["log_J"])
    bounds={"C10":[.05,2],"K0":[10,1000]}
    initial=Material("neo_hooke","quadratic_J",dict(C10=8,K0=5000)) # outside bounds; ignored by automatic mode
    args=dict(starts=2,max_nfev=60,pool_size=16,bounds=bounds,initialization="bounded")
    a=fit(d,initial,Objective(),seed=12,**args)
    b=fit(d,initial,Objective(),seed=12,**args)
    c=fit(d,initial,Objective(),seed=13,**args)
    assert a["initialization"]==b["initialization"]
    assert a["initialization"]["starting_parameters"]!=c["initialization"]["starting_parameters"]
    for candidate in a["candidates"]:
        for k,(lo,hi) in bounds.items():assert lo<=candidate["initial_parameters"][k]<=hi
    for k,v in truth.parameters.items():
        assert_allclose(a["candidates"][a["recommended_index"]]["parameters"][k],v,rtol=2e-4)
    assert_allclose(a["candidates"][0]["curves"]["stress"],b["candidates"][0]["curves"]["stress"],rtol=1e-12)


def test_random_pool_rejects_physically_invalid_samples():
    m=Material.default("polynomial2","quadratic_J");p=uniaxial(m,np.linspace(0,.6,12))
    d=Dataset(p["log_strain"],p["stress"],p["log_J"])
    r=fit(d,m,Objective(),starts=1,max_nfev=10,pool_size=32,seed=1)
    assert r["initialization"]["rejection_reasons"]
    assert any(not v["valid"] for v in r["initialization"]["sample_records"])
