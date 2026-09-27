# SPDX-License-Identifier: GPL-3.0-or-later
"""Trace of a symmetric positive-definite matrix power, including repeated roots.

For f(A)=tr(A**q), grad f=V diag(q*d**(q-1)) V.T. The Hessian
uses the divided difference of g(d)=q*d**(q-1), with g'(d) at
coincident roots. This avoids differentiating eigenvectors individually and
does not perturb the undeformed material into an anisotropic state.
"""
import numpy as np
import tensortrax.math as tm


def _eigen(a):
    d,v=np.linalg.eigh(np.moveaxis(a,(0,1),(-2,-1)))
    if np.any(d<=0):raise ValueError("Positive definite tensor required for Ogden energy")
    return d,v


def trace_power(a,q):
    if q==1:return tm.trace(a)

    def value(a):
        d,_=_eigen(a)
        return np.sum(d**q,axis=-1)

    def gradient(a):
        d,v=_eigen(a)
        g=np.einsum("...ia,...a,...ja->...ij",v,q*d**(q-1),v)
        return np.moveaxis(g,(-2,-1),(0,1))

    def hessian(a):
        d,v=_eigen(a)
        gap=d[..., :,None]-d[...,None,:]
        mid=(d[..., :,None]+d[...,None,:])/2
        g=q*d**(q-1)
        near=abs(gap)<=1e-7*mid
        divided=np.divide(g[..., :,None]-g[...,None,:],gap,
                          out=np.zeros_like(gap),where=~near)
        limit=q*(q-1)*mid**(q-2)
        limit+=q*(q-1)*(q-2)*(q-3)/24*mid**(q-4)*gap**2
        divided=np.where(near,limit,divided)
        h=np.einsum("...ab,...ia,...jb,...ka,...lb->...ijkl",divided,v,v,v,v,optimize=True)
        h=(h+h.swapaxes(-2,-1))/2
        return np.moveaxis(h,(-4,-3,-2,-1),(0,1,2,3))

    return tm.external(a,value,gradient,hessian)
