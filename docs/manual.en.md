# HyperFit user manual

[中文](manual.zh.md) · [English](manual.en.md) · [日本語](manual.ja.md)

## Start and choose a language

Follow the [deployment guide](deployment.en.md), then open http://127.0.0.1:8765. Choose English, 中文 or 日本語 in the header. The choice is saved in this browser; ?lang=en, ?lang=zh and ?lang=ja override it. Changing language preserves the loaded data, settings, seed, running job and selected candidate. Reloading the page starts a fresh UI session, so export results before reloading. Exported field names and parameter names stay language-independent.

The example is synthetic, with artificial noise. It is a workflow demonstration, not experimental validation. The User manual link opens this document in the selected language.

## Import measurements

Use CSV, TSV or XLSX with column names in the first row; convert legacy XLS first. Select a worksheet, the axial-strain, stress and volume columns, and their definitions. The interactive fitter accepts 4–3000 aligned finite observations with strictly increasing axial strain. Select one loading branch; explicitly arrange a compression branch in increasing-strain order. Do not combine loading/unloading, duplicates or unrelated specimens. Files are limited to 10 MB and worksheets to 50000 rows. Invalid cells are reported without silently deleting or sorting them.

Internal conventions are logarithmic axial strain ln λ, Cauchy stress σ in MPa and logarithmic volume strain ln J, where J = current volume / reference volume. Available conversions are engineering strain λ−1 or stretch λ; Pa, kPa or MPa; nominal stress P converted by σ = P λ/J; and volume J−1 or J converted to ln J. Do not confuse ln J with J−1 or infer stress definitions from magnitude. For homogeneous diagonal deformation, ln J is the sum of the three principal logarithmic strains.

With a local server, data remain on that machine. With a remote server, imports and run records are sent to and stored on that server. Review the raw measurement conventions before fitting.

## Combine material models

Choose a deviatoric energy: Neo-Hookean, Mooney–Rivlin, second-order Polynomial, Yeoh or Ogden with 1–3 terms. Choose a volume energy independently:

- quadratic_J: K0/2 · (J−1)².
- quadratic_logJ: K0/2 · (ln J)².
- exponential_logJ: K0/(2β) · [exp(β(ln J)²)−1]. At β=0 it continuously reduces to quadratic_logJ.
- polynomial2_J: (J−1)²/D1 + (J−1)⁴/D2.

The reconstructed manuscript combination is Mooney–Rivlin plus exponential_logJ. It was reimplemented from the energy formula; the lost source and manuscript experiments have not been recovered or reproduced. Material moduli are in MPa, D parameters in inverse MPa, and β and Ogden α are dimensionless.

Ogden uses Σᵢ 2μᵢ/αᵢ² (Σₖ λ̄ₖ^αᵢ−3), with initial shear modulus Σμᵢ. Check this convention before comparing coefficients with other software. Default positive μ and alternating positive/negative α bounds are a restricted parameterization. Each α interval must exclude zero. Permuting terms creates equivalent energies.

Although energies are modular, stress and volume are coupled. For every axial stretch the solver enforces zero lateral stress to determine transverse contraction and J. It does not assume incompressibility or fit the two curves independently. The current fit assumes isotropic, homogeneous uniaxial deformation.

## Choose initial values and search bounds

Expand Initial values and bounds. Bounds are search constraints, not evidence of stability. Generic demonstration ranges must be adjusted to the material scale. Some polynomial coefficients can be negative, but the initial shear modulus and solved path must remain admissible.

Under Preferences and compute budget, bounded initialization draws a seeded Latin hypercube pool (default 48 samples). Positive moduli use logarithmic coordinates; other parameters use linear coordinates. Each point is checked with the coupled forward response. Valid points are ranked by the joint objective, and separated points are selected as starts. Manual mode instead uses the entered initial values first, then nearby perturbations.

The seed is an integer from 0 to 4294967295; use 1–10 starts and 5–500 evaluations per start. The pool supports 10–256 samples. An inadequate valid pool is an error; revise bounds or enlarge it. Same data, bounds, seed and software versions reproduce sampling and fitting; different seeds help assess initialization sensitivity. A seed does not make an unreasonable range physical. Weight sweeps reuse the same starts to isolate weight effects.

## Select an error criterion

Peak-normalized RMSE divides RMSE by the observed absolute channel peak. Equal absolute errors contribute equally; equal percentage errors contribute more at larger signals. Pointwise relative error is also problematic near zero. No single metric establishes the best scientific model.

The default absolute-plus-relative tolerance uses s(y) = sqrt(a² + (b|y|)²). Set separate absolute stress and volume scales and a relative fraction. This keeps the origin finite while controlling large-signal influence. The objective integrates over strain with trapezoidal weights so dense sampling alone does not dominate. Soft-L1 and Huber reduce outlier influence; squared loss does not. Robust transformation precedes integration weighting.

Tolerances and optional low-strain weights are research preferences, not measurement standard deviations or confidence intervals. If a credible standard-deviation model is known for independent observations, select Known standard deviation and squared loss for weighted least squares under independent Gaussian errors. This mode disables preference weighting and tradeoff sweeps in the submitted request. Correlated errors, DIC systematic error and uncertainty in the strain coordinate are not modeled.

## Compare candidates

Start joint fit and inspect both response curves, low-strain zoom, residuals, convergence, bound hits and sensitivity. The residual plot always shows raw prediction-minus-observation divided by each channel peak. It is not the robust weighted objective. The candidate table reports peak NRMSE; the tradeoff scatter uses ordinary RMSE, with MPa horizontally and ln J vertically.

Explore stress / volume tradeoffs repeats local searches at three weight ratios, roughly tripling computation. Non-dominated means no explored candidate improves one displayed error without worsening the other. This is a finite explored set, not a proven global Pareto front, and a knee is not automatically the correct material. Use it to study preferences after defining valid data and error scales.

Click a row or scatter point, or use Enter, to select a candidate and update curves. A budget-limited result is diagnostic. Default qualification requires optimization convergence and a positive sampled acoustic-tensor screen; finite states and directions do not prove global stability. High or unavailable sensitivity condition numbers and boundary hits warrant investigation. Similar curves need not imply identifiable, unique parameters. Additional loading modes, repeats and held-out ranges are valuable checks.

## FEM verification and exports

Run cube check uses the selected fitted parameters, or entered material parameters before fitting. The three-field u/p/J mixed FElupe cube contracts freely laterally and is compared with an independent material-point stress calculation. The UI cube is homogeneous. It is neither a fit to the original specimen geometry nor Abaqus/UHYPER/UMAT validation.

The command-line verification also includes clamped nonuniform examples and refinement. Reaction-force convergence alone does not establish volume accuracy: inspect mixed J against det(F), and distinguish mean(ln J) from ln(mean J). The existing nonuniform checks do not yet establish converged local volume fields. See [validation evidence](VALIDATION.md).

Export run record downloads JSON with input data, model, search bounds, seed, initialization diagnostics, objective, candidates, selected index, dependency versions and scientific-source hashes. Server records are stored in runs/<job-id>/ or HYPERFIT_RUNS. Completed records can be queried by ID after restart; unfinished jobs become interrupted. The UI has no historical-run browser or one-click JSON replay yet. Cancelling FEM takes effect after the current increment.

## Troubleshooting and maintenance

Use the localized error summary and expand Technical details for the unmodified diagnostic. If no valid candidate exists, first check units, definitions, strain range and physical bounds. A failed solve should not be hidden by dropping measurements. Use a different local port if 8765 is occupied.

Translations live in hyperfit/frontend/locales/{zh,en,ja}.json. Keep keys and placeholders aligned; scientific IDs and equations do not change with locale. Browser manuals are generated from these Markdown files by tools/build_manuals.py. Run the tests and regenerate manuals after edits. See [contribution guide](CONTRIBUTING.md) and [method conventions](methods.md).

GPL-3.0-or-later applies to the reconstructed public code. No original experimental workbooks, manuscript PDF or legacy simulation outputs are included.
