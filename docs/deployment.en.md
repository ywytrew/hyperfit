# HyperFit deployment guide

[中文](deployment.zh.md) · [English](deployment.en.md) · [日本語](deployment.ja.md)

## Get the code

This deploys the Python API and the complete trilingual web interface. Python 3.12 is recommended; the project requires at least 3.11. Install Git and Python first. No Node/npm build, GPU or Abaqus installation is required.

```text
git clone https://github.com/ywytrew/hyperfit.git
cd hyperfit
```

## Windows

Run from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

Open http://127.0.0.1:8765. Chinese is the initial default; select English or use ?lang=en, or ?lang=ja for Japanese. Later, double-click start.cmd. Press Ctrl+C to stop. If PowerShell blocks the launcher, use the direct Python command above without changing system execution policy. For a busy port, replace 8765 with 8766, or run ./start.ps1 -Port 8766.

## Linux / macOS

Prepare Python 3.12 with venv support, then run from the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

Open the same local address; Ctrl+C stops the process. Keep one worker. Job state and cancellation currently belong to one process, so increasing Uvicorn workers is not a supported scaling method.

## Docker Compose

Install and start Docker Engine 28+ or corresponding Docker Desktop with Linux containers, and the Compose plugin. The development PC had no running Docker daemon, so the container was not run locally; repository CI includes a build and HTTP smoke check.

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 hyperfit
# Stop without removing saved runs:
docker compose down
```

The container listens on 0.0.0.0:8765 internally, while Compose publishes only 127.0.0.1:8765 on the host. It runs as a non-root user with one worker. The hyperfit-runs named volume retains records at /data. Only application sources and locked dependencies enter the image, not local experiments or runs. The health check requests /api/models. Do not use down -v unless you intend to delete the run volume.

If host port 8765 is occupied, change the mapping in compose.yaml to 127.0.0.1:8766:8765 and browse port 8766. Changing only the browser address is insufficient.

## Remote server through SSH

Clone and start the native or Docker version on your own server. Keep it bound to loopback; do not open firewall port 8765. On the researcher's computer, substitute the SSH account and hostname:

```sh
ssh -N -L 8765:127.0.0.1:8765 your-user@your-server
```

Keep that SSH session open and browse http://127.0.0.1:8765 locally. If needed, change the tunnel's leftmost port to 8766. Imported data and records are processed and stored on the remote server. This application has no built-in authentication, user isolation or quotas. This guide therefore uses SSH access. A public multiuser service needs authentication, HTTPS, access control and a compute queue design; changing the bind address alone is insufficient.

## Frontend, backend and records

The default service serves static frontend files and /api/* together, while scientific Python modules are independent of the UI. A separate frontend may set window.HYPERFIT_API before loading app.js. Development CORS allows only localhost:5173 and 127.0.0.1:5173. Prefer a same-origin reverse proxy for a managed deployment. GitHub Pages cannot execute the Python/FEM backend.

Native runs default to runs/ in the repository. Set HYPERFIT_RUNS to a dedicated writable directory before startup to relocate them. Docker uses the named volume at /data. Back up the complete directory or volume and protect exported JSON containing measurements. Interrupted jobs do not resume automatically. Before updating, export records, back up runs and record git rev-parse HEAD. Stop, git pull --ff-only, install the lock file or rebuild Compose, and restart. To roll back, check out the old commit in a separate directory and recreate its environment without overwriting uncommitted work.

## Verify and maintain

Use the virtual environment's Python (Windows: .venv/Scripts/python.exe; Linux/macOS: .venv/bin/python):

```sh
python -m pytest -q
python -m hyperfit.verify --output validation-results/fem-verification.json
python tools/build_manuals.py
python tools/package_source.py
```

Browser acceptance: load the synthetic example, fit, switch languages, select a candidate, run the cube check and export JSON. Interactive API documentation is at /docs. Scientific limits are in the [manual](manual.en.md) and [validation record](VALIDATION.md). Windows native execution was tested on the development PC; consult actual Actions results for Linux and container validation. macOS has not been tested on hardware.

Official networking and service references: [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) · [Uvicorn deployment](https://uvicorn.dev/deployment/)
