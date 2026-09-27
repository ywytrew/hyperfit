# Third-party components

HyperFit uses unmodified dependencies installed from PyPI. They are not copied into the source release. Their licenses remain with their respective authors.

| Component | Purpose | License metadata inspected in the installed distribution |
|---|---|---|
| FElupe 10.1.0 | FE assembly, mixed formulation, Newton solution | GPL-3.0-or-later |
| tensortrax 0.26.2 | automatic differentiation | GPL-3.0-or-later |

Both are maintained by Andreas Dutzler and their contributors. See [FElupe](https://github.com/adtzlr/felupe) and [tensortrax](https://github.com/adtzlr/tensortrax) for original source and notices.

Other Python dependencies and exact versions are listed in `requirements-lock.txt`; their installed distribution metadata contains their license notices. The GNU GPL text in `LICENSE` was obtained from <https://www.gnu.org/licenses/gpl-3.0.txt>.

The frontend is plain JavaScript, CSS and HTML, with no remotely loaded libraries, fonts or telemetry. Prettier 3.8.1 was used as a development formatter and is not required to run the application. The constitutive formulas, spectral derivative primitive, analytic material-point solver, objectives and frontend are newly implemented for this project.
