# HyperFit

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

Joint stress–volume calibration for isotropic hyperelastic materials. Research preview 0.1.0, GPL-3.0-or-later.

- [User manual](docs/manual.en.md): data definitions, models, seeded initialization, fitting criteria, candidate selection and verification.
- [Deployment guide](docs/deployment.en.md): Windows, Linux/macOS, Docker Compose and remote access through SSH.
- [Mathematical conventions](docs/methods.md), [validation evidence](docs/VALIDATION.md), [contributing](docs/CONTRIBUTING.md).

## Quick start

Python 3.12 recommended. Clone this repository, create a virtual environment and install requirements-lock.txt. Run from the repository root:

```sh
python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

Use the virtual environment's Python. Open http://127.0.0.1:8765/?lang=en. No frontend build is required. Choose 中文, English or 日本語 in the header; switches preserve current inputs and results. Full platform commands are in the deployment guide.

## What it does

Combine Neo-Hookean, Mooney–Rivlin, Polynomial, Yeoh or Ogden energies with one of four volume energies, including K0/(2β)[exp(β(ln J)²)−1]. The forward solve enforces zero transverse stress, coupling stress and volume. Bounded, seeded Latin hypercube initialization screens coupled responses before multistart fitting; manual starts remain available.

Absolute-plus-relative tolerances, robust loss and strain-interval weighting make error preferences explicit. Known-noise weighting and peak NRMSE are available. A three-weight exploration displays non-dominated candidates among local searches, not a proven global Pareto front. Residuals, bounds, convergence and sensitivity accompany the curves.

The independent material-point calculation is checked with mixed u/p/J FElupe elements. Sampled acoustic tensors screen candidate stability, but do not prove global stability. The UI fits homogeneous uniaxial data; it does not invert the original specimen geometry. Nonuniform volume accuracy needs further validation. No Abaqus execution or UHYPER/UMAT exporter is provided.

Only reconstructed code, documentation, tests and synthetic examples are public. Lost code was not recovered and original experiments were not reproduced. Original measurements and the manuscript are excluded. The server is a local research tool without built-in multiuser authentication; use the deployment guide's SSH workflow for remote access.

## Development

```sh
python -m pytest -q
python -m hyperfit.verify --output validation-results/fem-verification.json
python tools/build_manuals.py
python tools/package_source.py
```

API: /docs. Scientific modules are independent of HTTP; the frontend uses /api/* JSON. Locale files are in hyperfit/frontend/locales/. Preserve keys and placeholders across all three languages. Browser manuals are generated from docs/manual.*.md and docs/deployment.*.md.

See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
