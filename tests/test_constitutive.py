# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
import pytest
from numpy.testing import assert_allclose
from hyperfit.models import Material, DEVIATORIC, VOLUMETRIC, uniaxial
from hyperfit.fem import ad_material
from hyperfit.stability import acoustic_screen


@pytest.mark.parametrize("dev",DEVIATORIC)
@pytest.mark.parametrize("vol",VOLUMETRIC)
def test_analytic_stress_matches_independent_ad(dev,vol):
    material=Material.default(dev,vol)
    umat=ad_material(material)
    for l in ([1,1,1],[1.25,.90,.89],[.85,1.08,1.08]):
        f=np.diag(l)
        p=umat.gradient([f[:,:,None,None]])[0][...,0,0]
        sigma=p@f.T/np.linalg.det(f)
        assert_allclose(sigma,np.diag(material.principal_cauchy(l)),rtol=2e-10,atol=2e-10)


@pytest.mark.parametrize("dev",DEVIATORIC)
def test_ad_tangent_finite_difference_and_objectivity(dev):
    material=Material.default(dev)
    umat=ad_material(material)
    f=np.array([[1.1,.13,0],[0,.97,.04],[0,0,.94]])
    grad=lambda f:umat.gradient([f[:,:,None,None]])[0][...,0,0]
    a=umat.hessian([f[:,:,None,None]])[0][...,0,0]
    h=1e-6
    for j in range(3):
        for k in range(3):
            d=np.zeros((3,3));d[j,k]=h
            assert_allclose(a[:,:,j,k],(grad(f+d)-grad(f-d))/(2*h),rtol=2e-6,atol=2e-6)
    angle=.53
    r=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
    assert_allclose(grad(r@f),r@grad(f),rtol=2e-10,atol=2e-10)


@pytest.mark.parametrize("vol",VOLUMETRIC)
def test_volume_derivatives_and_reference(vol):
    m=Material.default(volumetric=vol)
    w,d1,d2=m.volume(np.array([1.]))
    assert_allclose([w[0],d1[0]],[0,0],atol=1e-13)
    expected=m.parameters.get("K0",2/m.parameters.get("D1",1))
    assert_allclose(d2,[expected])
    j=np.array([.982,1.,1.018]);h=1e-6
    assert_allclose(m.volume(j)[1],(m.volume(j+h)[0]-m.volume(j-h)[0])/(2*h),rtol=1e-7,atol=1e-8)
    assert_allclose(m.volume(j)[2],(m.volume(j+h)[1]-m.volume(j-h)[1])/(2*h),rtol=1e-7)


def test_beta_zero_is_log_squared_not_j_squared():
    a=Material("mooney_rivlin","exponential_logJ",dict(C10=.4,C01=.15,K0=100,beta=0))
    b=Material("mooney_rivlin","quadratic_logJ",dict(C10=.4,C01=.15,K0=100))
    assert_allclose(a.volume([.9,1,1.1]),b.volume([.9,1,1.1]))
    assert not np.isclose(a.volume([1.1])[0][0],.5*100*.1**2)


def test_ogden_neo_hookean_limit_and_free_lateral_faces():
    ogden=Material("ogden1","quadratic_J",dict(mu1=1.2,alpha1=2,K0=1000))
    neo=Material("neo_hooke","quadratic_J",dict(C10=.6,K0=1000))
    x=np.linspace(-.25,.5,31)
    a,b=uniaxial(ogden,x),uniaxial(neo,x)
    assert_allclose(a["stress"],b["stress"],atol=2e-12)
    assert_allclose(a["lateral_stress"],0,atol=1e-9)
    assert_allclose(a["stress"]/3,ogden.volume(np.exp(a["log_J"]))[1],atol=1e-9)
    assert np.max(abs(a["log_J"]))>1e-4


def test_acoustic_screen_detects_deliberately_unstable_polynomial():
    stable=Material.default()
    assert acoustic_screen(stable,np.array([np.eye(3)]))["positive_at_samples"]
    bad=Material("polynomial2","quadratic_J",dict(C10=.4,C01=.1,C20=-4,C11=0,C02=0,K0=100))
    f=np.diag([1.6,1/np.sqrt(1.6),1/np.sqrt(1.6)])
    assert not acoustic_screen(bad,np.array([f]))["positive_at_samples"]


@pytest.mark.parametrize("alpha",[-3.71,-2.,.43,2.36,5.77])
@pytest.mark.parametrize("stretches",[[1,1,1],[1.2,.92,.92],[1.2,.92,.92000000001]])
def test_ogden_repeated_eigenvalues_have_consistent_stress_and_tangent(alpha,stretches):
    m=Material("ogden1","quadratic_J",dict(mu1=1.1,alpha1=alpha,K0=100))
    umat=ad_material(m);f=np.diag(stretches)
    grad=lambda f:umat.gradient([f[:,:,None,None]])[0][...,0,0]
    sigma=grad(f)@f.T/np.linalg.det(f)
    assert_allclose(sigma,np.diag(m.principal_cauchy(stretches)),atol=2e-12,rtol=1e-11)
    a=umat.hessian([f[:,:,None,None]])[0][...,0,0]
    h=1e-6
    for j,k in [(0,0),(0,1),(1,2),(2,2)]:
        d=np.zeros((3,3));d[j,k]=h
        assert_allclose(a[:,:,j,k],(grad(f+d)-grad(f-d))/(2*h),atol=3e-7,rtol=3e-7)


@pytest.mark.parametrize("j",[0,-1,float("nan"),float("inf")])
def test_nonphysical_j_rejected(j):
    with pytest.raises(ValueError):Material.default().volume(j)
