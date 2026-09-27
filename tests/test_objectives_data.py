# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import numpy as np
import pytest
from numpy.testing import assert_allclose
from hyperfit.objectives import Dataset,Objective,metrics,non_dominated
from hyperfit.data import normalize,read_table


def sample(n=11):
    x=np.linspace(0,1,n)
    return Dataset(x,2*x,.01*x)


@pytest.mark.parametrize("loss",["linear","soft_l1","huber"])
def test_robust_threshold_does_not_depend_on_number_of_samples(loss):
    # Constant normalized residual has exactly the same integral on either grid.
    obj=Objective(stress_relative=0,volume_relative=0)
    costs=[]
    for n in (11,101,1001):
        d=sample(n)
        p={"stress":d.stress+.2,"log_J":d.log_J+.0004}
        r=obj.residuals(d,p,loss)
        costs.append(np.dot(r,r))
    assert_allclose(costs,costs[0],rtol=1e-12)


def test_uncertainty_linear_loss_is_chi_squared_and_samples_count():
    d=sample();obj=Objective(mode="uncertainty",sampling="observations",stress_relative=0,volume_relative=0)
    r=obj.residuals(d,{"stress":d.stress+.02,"log_J":d.log_J+.0002})
    assert_allclose(np.dot(r,r),2*len(d.stress))
    with pytest.raises(ValueError):Objective(mode="uncertainty")


def test_zero_signal_and_small_strain_floor():
    d=Dataset(np.linspace(0,.3,5),np.zeros(5),np.zeros(5))
    p={"stress":np.zeros(5),"log_J":np.zeros(5)}
    assert_allclose(Objective().residuals(d,p),0)
    assert metrics(d,p)["stress"]["peak_nrmse"] is None
    with pytest.raises(ValueError):Objective(mode="peak").residuals(d,p)


def test_measure_and_unit_conversion():
    x=np.linspace(0,.4,5);v=.01*x;s=2*x
    nominal=s*np.exp(v-x)
    rows=np.array([np.expm1(x),nominal*1e6,np.expm1(v)]).T.tolist()
    d=normalize(rows,0,1,2,"engineering","nominal","J_minus_1","Pa")
    assert_allclose(d.log_strain,x);assert_allclose(d.stress,s);assert_allclose(d.log_J,v)
    rows=np.array([x,s,v]).T.tolist()
    with pytest.raises(ValueError):normalize(rows,-1,1,2,"log","cauchy","log_J","MPa")
    with pytest.raises(ValueError):normalize(rows,0,1,1,"log","cauchy","log_J","MPa")
    rows[1][0]=rows[0][0]
    with pytest.raises(ValueError,match="monotonic"):normalize(rows,0,1,2,"log","cauchy","log_J","MPa")


def test_csv_retains_first_observation_and_rejects_blank_selected_cells():
    csv="strain,stress,log_J\n0,0,0\n.1,1,.001\n.2,2,.002\n.3,3,.003\n"
    table=read_table("sample.csv",base64.b64encode(csv.encode()).decode())
    assert len(table["rows"])==4 and table["rows"][0]==["0","0","0"]
    table["rows"][2][1]=""
    with pytest.raises(ValueError):normalize(table["rows"],0,1,2,"log","cauchy","log_J","MPa")


def test_non_dominated_and_nan_exclusion():
    assert non_dominated([[1,2],[2,1],[3,3],[1,2],[float("nan"),0]])==[0,1,3]
