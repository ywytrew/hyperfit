# Local validation record — 2026-09-27

Environment: Windows, Python 3.12.14; dependency versions are in the lock file. These are local verification results, not a claim about the original physical specimen or Abaqus.

## Automated suite

`python -m pytest -q`: **91 passed**. One third-party deprecation warning concerns Starlette's httpx TestClient; it does not represent a scientific test failure. Coverage includes all 28 energy combinations, derivatives and objectivity, Ogden repeated eigenvalues and special limits, noise-free parameter recovery with unseen strains, robust sampling invariance, data conversions, seed reproducibility, invalid-start rejection, cancellation, API persistence/export and finite elements. The additional frontend checks cover translation key/placeholder parity and synchronization of all six browser documents.

Tests establish these cases, not correctness for every possible parameter vector or deformation.

## Independent constitutive/FEM comparisons

Paper-formula verification parameters: C10=0.4642 MPa, C01=0.434 MPa, K0=230 MPa, beta=34000. They are a test case, not a newly calibrated material.

Free lateral contraction cube, Hex8/P0/P0, 1/8/27 cells, 12 increments, final stretch 0.85 and 1.5:

- Maximum nominal stress difference from analytic principal-stress response: **4.73e-13 MPa** (rounded upward).
- Maximum log-volume difference: **3.87e-14**.

This is a homogeneous patch test. Extremely small errors are expected for a homogeneous exact solution; they do not demonstrate nonuniform mesh accuracy.

## Clamped nonuniform cube

Same material, final stretch 1.3, one loaded face transversely clamped with symmetry planes. `log total volume` means logarithm of the global current/reference volume ratio; `mean log J` is a reference-volume weighted mean of the geometric local logarithm.

| Formulation | Cells | Nominal reaction / MPa | log total volume | mean log J | max difference: geometric J minus mixed J |
|---|---:|---:|---:|---:|---:|
| Hex8/P0/P0 | 8 | 1.39752450 | 0.00279249 | -0.00014095 | 0.14279 |
| Hex8/P0/P0 | 27 | 1.37586337 | 0.00272833 | 0.00138308 | 0.14064 |
| Hex8/P0/P0 | 64 | 1.36668724 | 0.00270090 | 0.00189785 | 0.14562 |
| Hex8/P0/P0 | 216 | 1.35895393 | 0.00267813 | 0.00227685 | 0.15876 |
| Hex27/Q1d/Q1d | 1 | 1.36414586 | 0.00270372 | 0.00089141 | 0.10368 |
| Hex27/Q1d/Q1d | 8 | 1.35609905 | 0.00267306 | 0.00231188 | 0.10232 |
| Hex27/Q1d/Q1d | 27 | 1.35332835 | 0.00266306 | 0.00250105 | 0.11174 |
| Hex27/Q1d/Q1d | 64 | 1.35209969 | 0.00265894 | 0.00256116 | 0.12035 |

Successive Hex8 reaction differences: 1.574%, 0.671%, 0.569%. Hex27 reaction from 27 to 64 cells changes about 0.091%, but mean log J changes about 2.35%. Pointwise geometric/mixed J differences remain large near constrained regions and do not converge monotonically.

**This benchmark does not pass as evidence of accurate local volume fields.** Higher order improves the reported averages, but reaction convergence alone is insufficient for volume calibration. Boundary singularities, approximation spaces and the actual experimental observation region need a dedicated convergence study before nonuniform FE inversion. The web's free cube check remains a constitutive patch check, explicitly labelled as such.

## Sampled strong ellipticity

For the same parameters, checked 22 specified gradients: 11 traction-free uniaxial states with stretches 0.8..1.65, determinant-one biaxial and planar states, simple shear, and small hydrostatic dilations/compressions. 203 directions per state (axes plus seeded directions). Minimum reference acoustic eigenvalue approximately **1.09985679 MPa**, positive at these samples.

Positive samples do not prove global material stability or reproduce Abaqus diagnostics. Full checked matrices, directions/settings, cube responses and mesh metrics are saved by `python -m hyperfit.verify`; the generated JSON is intentionally excluded from the source archive and can be reproduced.

## Browser and provenance

Local browser exercised synthetic joint fitting, live candidate curves/table, sampled-stability labels and selected-model FEM comparison. API tests verify explicit column conversions, downloadable JSON with selected candidate, and saved-result recovery. Only synthetic data were used for this workflow.

The recovered project's separate audit read 11 worksheets and checked original-source hashes without changing the old files. Real-data calibration still requires confirmation of stress measure/area, experiment grouping and the intended observation operator. No manuscript or experimental workbook is included in this distribution.
