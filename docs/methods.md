# Numerical and scientific conventions

All energies are per reference volume. `J=det(F)>0`, `Fbar=J^(-1/3)F`, and `W=Wdev(I1bar,I2bar or principal stretches)+U(J)`. Moduli are in MPa.

## Exponential logarithmic volumetric energy

Let `t=ln J`, `E=exp(βt²)`:

```text
U  = K0/(2β) expm1(βt²)
U' = K0 E t/J
U''= K0 E (1−t+2βt²)/J²
U'''=K0 E [−3+(2+6β)t−6βt²+4β²t³]/J³
```

The β=0 energy is exactly `K0 t²/2`, not `K0(J−1)²/2`. `U''(1)=K0`. The tangent bulk response along a uniform dilation is `J U''(J)`. `K0>0` and `β>=0` do not automatically establish global convexity: the β=0 energy has negative curvature for `ln J>1`.

## Homogeneous uniaxial solver

For prescribed `x=ln λ1`, solve for `v=ln J` using
`λ=[exp(x),exp((v−x)/2),exp((v−x)/2)]` and `σ22=0`. The bracket is `|v|<=min(0.5,sqrt(500/β))` for β>0, otherwise 0.5. Input `|x|<=2`; this is a numerical domain, not an applicability claim. Bracketing failure, overflow, lateral imbalance, negative `U''` or nonpositive transverse equilibrium slope invalidates a trial. Multiple equilibrium branches are not exhaustively tracked; nonmonotone constitutive laws require separate path-following analysis.

Analytic principal Cauchy stresses are independently implemented from the FE energy derivative. For invariant models:

```text
σ_i = 2/J [W1 (bbar_i−I1bar/3) − W2 (1/bbar_i−I2bar/3)] + U'(J)
```

For Ogden, sum `2 μ/α/J (λbar_i^α−mean(λbar^α))`, then add `U'`. The FE implementation of `tr(Cbar^q)` uses divided differences of `g(d)=q d^(q−1)` and the derivative limit at coincident eigenvalues. It does not rely on eigenvalue perturbation. Test noninteger powers, both signs, repeated roots and objectivity when changing this code.

## Loss, sampling and interpretation

For channel c, define `r_ci=(prediction−observation)/s_ci`, with tolerance scale `s_ci=sqrt(a_c²+(b_c |observation|)²)`. Objective is
`0.5 Σ_c importance_c Σ_i w_i ρ(r_ci²)`.
Trapezoidal strain weights are normalized to sum to one per channel. Optional low-|strain| preference modifies those weights and is recorded. Robust thresholds operate on r before weighting. Peak mode uses `max(abs(observation))`, rejects identically zero signals, and retains a specific reproducible NRMSE definition.

Known-uncertainty mode uses observation weights of one without normalizing the sample count and without extra preference weights. With a linear loss and known independent Gaussian standard deviations, twice the cost is the specified chi-squared statistic. The program does not estimate those standard deviations, account for correlation, or provide uncertainty intervals. Robust loss changes that statistical interpretation.

The current uncertainty scale is diagonal and uses measured magnitudes, so it is a chosen approximation to heteroscedastic noise, not a general fitted probability model. If the variance depends on predictions and is fitted jointly, a likelihood must include its normalization terms. For correlated errors, replace diagonal normalization with covariance whitening. If axial strain uncertainty is material, use an errors-in-variables or joint observation formulation. These extensions are not implemented here.

## Parameter selection

Automatic initialization uses a seeded Latin hypercube in transformed coordinates. Each sampled point undergoes a full coupled forward solve and common-objective evaluation. Valid points are ranked; starting points are selected in rank order with RMS coordinate distance at least 0.15 where possible, then filled by remaining best points if necessary. This heuristic keeps useful starting points apart but does not prove coverage of all attraction basins. If too few valid samples remain the request fails explicitly instead of inventing replacement parameters.

Manual mode retains the entered first point and nearby random perturbations. The same starting pool is reused across tradeoff weights. Initialization sampling and optimization evaluation budgets are separate and both are recorded. The initial screening checks admissible equilibrium/local path conditions; final candidates undergo the additional directional acoustic check.

Search variables are scaled to [0,1], positive moduli use logarithms by default. Multiple starts use a recorded random seed. `max_nfev` is SciPy's per-start residual evaluation limit excluding numerical-Jacobian calls; the UI reports the actual counted calls, which can exceed this limit. Failed forward evaluations return fixed penalties but are not retained as final valid solutions. Stationary invalid regions can trap a local start; inspect failure counts and vary bounds/starts.

Candidates are checked for convergence, bound hits, raw residual Jacobian condition and sampled strong ellipticity. The Jacobian is with respect to the scaled search coordinates, so its condition depends on the chosen parameterization and ranges. It is not a confidence interval or a binary identifiability test. Profiles, grouped bootstrap and held-out complete experiments are recommended future validation, not implemented claims.

The optional weight sweep is 0.1, 1, 10 times the original volume importance. Scores are recomputed under a common base objective before ranking. Non-dominated marks use raw channel RMSE, so the displayed scatter axes are not the robust/tolerance objective. A weighted-sum sweep can miss nonconvex portions of a Pareto set. The default choice is the lowest common objective among converged, sampled-stable candidates; if none qualify the interface explicitly labels the result diagnostic.

## FEM and stability evidence

FElupe supplies FE assembly and Newton solution. Stress and material tangents follow tensortrax automatic differentiation of the energy, with an analytic spectral derivative primitive for Ogden. `Hex8/P0/P0` and `Hex27/Q1d/Q1d` use displacement, pressure and dilatation fields. Neither a successfully converged Newton solve nor a homogeneous patch test certifies nonuniform mesh accuracy.

Record separately:

- Reference-volume weighted mean of `ln(det F)`;
- Logarithm of total current/reference volume, `ln(∫det F dV0 / ∫dV0)`;
- Mean of the independent mixed-field `ln J`;
- Maximum difference between `det F` and the mixed J field.

These are equal for uniform deformation but are distinct observables for a nonuniform specimen. Choose an observation operator corresponding to the actual experiment before FE inversion.

The acoustic tensor screen uses `A_iJkL=dP_iJ/dF_kL` and `Q_ik=A_iJkL n_J n_L`. It samples axes and seeded directions, then reports the minimum symmetric eigenvalue and the exact checked gradients. A negative value detects loss of strong ellipticity at a sampled state. Positive values do not prove global stability, prevent structural buckling, or reproduce Abaqus stability diagnostics.

## References

- [FElupe custom hyperelastic energies and automatic differentiation](https://felupe.readthedocs.io/en/latest/howto/umat_hyperelasticity.html)
- [FElupe mixed fields](https://felupe.readthedocs.io/en/latest/howto/mixed.html)
- [Abaqus hyperelastic conventions](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEMATRefMap/simamat-c-hyperelastic.htm)
- [SciPy bounded nonlinear least squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
- [NIST weighted least squares](https://itl.nist.gov/div898/handbook/pmd/section1/pmd143.htm)

The recovered project owner's supplied manuscript §3.2.2 defined the custom volume term. The manuscript and real experimental data are not included in this source distribution.
