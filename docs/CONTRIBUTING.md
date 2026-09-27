# Contributing

Work inside this standalone rebuild. Do not import old scripts from its parent directory: several execute jobs or write files during import. Do not add experimental workbooks, paper manuscripts, Abaqus jobs, credentials, virtual environments or local cache directories to a release.

For a model change, document the reference-volume energy, stress measure, coefficient convention, small-strain limit and intended deformation domain. Supply analytic/AD cross-checks, finite-difference tangent tests and limiting-case tests. For Ogden or another spectral model include repeated principal stretches and arbitrary rotations. A good fit alone is not model validation.

For objective changes, specify units, normalization, sampling measure and interpretation. Retest zeros, sign changes, unequal grid density and failed forward solves. Do not relabel researcher tolerances as measured uncertainty. For solver changes verify both force and volume observations; keep point/region/global averages distinct.

Run `python -m pytest -q` and, for FE changes, `python -m hyperfit.verify`. Review the output, including warnings and failed conditions. UI changes should be exercised from data import through fitting, candidate selection and export at a narrow and a desktop viewport. Keep Python core logic independent of HTTP and browser state.

Report a bug with the exported **synthetic or shareable** run configuration, dependency versions, error and expected observation. If using real experiments, obtain permission before attaching them. New contributions use GPL-3.0-or-later. Never claim Abaqus verification without recording the actual version, compiled subroutine and executed tests.

Translations live in `hyperfit/frontend/locales/{zh,en,ja}.json`. Keep keys and named placeholders aligned; do not translate scientific API IDs, parameter names or exported field names. Verify switching language during a job and after choosing a candidate without losing state. Preserve original diagnostics behind the translated error summary.

Update the corresponding Chinese, English and Japanese manuals when behavior changes. Edit `docs/manual.*.md` and `docs/deployment.*.md`, then run `python tools/build_manuals.py`; commit all six generated HTML files. No external Markdown renderer is required. Keep scientific cautions and deployment limitations equivalent across languages.
