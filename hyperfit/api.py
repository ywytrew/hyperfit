# SPDX-License-Identifier: GPL-3.0-or-later
"""Local API. Scientific modules remain independent of HTTP and the frontend."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import hashlib
import json
import os
from threading import Event, Lock
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
import numpy as np

from . import __version__
from .models import Material, DEVIATORIC, VOLUMETRIC, uniaxial
from .objectives import Dataset, Objective
from .fitting import fit, Cancelled
from .fem import cube_test
from .data import read_table, normalize
from .stability import acoustic_screen

app = FastAPI(title="HyperFit", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET","POST"], allow_headers=["Content-Type"])
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hyperfit")
lock = Lock()
jobs = {}
run_root = Path(os.environ.get("HYPERFIT_RUNS", Path(__file__).resolve().parents[1]/"runs"))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MaterialInput(StrictModel):
    deviatoric: str = "mooney_rivlin"
    volumetric: str = "exponential_logJ"
    parameters: dict[str,float]


class DataInput(StrictModel):
    name: str = "experiment"
    log_strain: list[float] = Field(min_length=4,max_length=3000)
    stress: list[float] = Field(min_length=4,max_length=3000)
    log_J: list[float] = Field(min_length=4,max_length=3000)


class FitRequest(StrictModel):
    material: MaterialInput
    data: DataInput
    objective: dict = Field(default_factory=dict)
    starts: int = Field(default=2,ge=1,le=10)
    max_nfev: int = Field(default=80,ge=5,le=500)
    loss: str = "soft_l1"
    seed: int = Field(default=42,ge=0,le=4294967295)
    initialization: str = "bounded"
    pool_size: int = Field(default=48,ge=10,le=256)
    tradeoff: bool = False
    bounds: dict[str,list[float]] | None = None


class FEMRequest(StrictModel):
    material: MaterialInput
    stretch: float = Field(default=1.2,ge=.7,le=1.7)
    cells: int = Field(default=2,ge=1,le=6)
    steps: int = Field(default=10,ge=2,le=50)
    clamped: bool = False


class ImportRequest(StrictModel):
    filename: str
    content: str = Field(max_length=14_000_000)
    sheet: str | None = None


class NormalizeRequest(StrictModel):
    rows: list
    strain_column: int
    stress_column: int
    volume_column: int
    strain_measure: str
    stress_measure: str
    volume_measure: str
    stress_unit: str
    name: str = "experiment"


def atomic_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),encoding="utf-8")
    tmp.replace(path)


def submit(kind, config, operation):
    job_id = uuid.uuid4().hex
    directory = run_root/job_id
    directory.mkdir(parents=True)
    canonical = json.dumps(config,sort_keys=True,allow_nan=False).encode()
    envelope = {"version": __version__, "kind": kind, "config": config,
                "created_at":datetime.now(timezone.utc).isoformat(),
                "dependencies":{k:version(k) for k in ("numpy","scipy","felupe","tensortrax","fastapi")},
                "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in Path(__file__).parent.glob("*.py")},
                "configuration_sha256": hashlib.sha256(canonical).hexdigest()}
    atomic_json(directory/"input.json", envelope)
    with lock:
        jobs[job_id] = {"status": "queued", "kind": kind, "progress": {}, "cancel": Event()}
    def update(progress):
        with lock: jobs[job_id]["progress"] = progress
    def work():
        try:
            with lock: jobs[job_id]["status"] = "running"
            if jobs[job_id]["cancel"].is_set(): raise Cancelled("Cancelled before start")
            result = operation(update,jobs[job_id]["cancel"])
            if jobs[job_id]["cancel"].is_set(): raise Cancelled("Cancelled")
            atomic_json(directory/"result.json", {**envelope,"result":result})
            with lock: jobs[job_id].update(status="completed",result=result)
        except Cancelled:
            with lock: jobs[job_id]["status"] = "cancelled"
        except Exception as exc:
            with lock: jobs[job_id].update(status="failed",error=str(exc))
        finally:
            with lock: snapshot = {k:v for k,v in jobs[job_id].items() if k not in ("cancel","result")}
            atomic_json(directory/"status.json",snapshot)
    executor.submit(work)
    return {"job_id":job_id}


@app.get("/api/models")
def models():
    return {"deviatoric":{k:{p:asdict(s) for p,s in v.items()} for k,v in DEVIATORIC.items()},
            "volumetric":{k:{p:asdict(s) for p,s in v.items()} for k,v in VOLUMETRIC.items()},
            "version":__version__, "units":"MPa", "abaqus_verified":False}


@app.get("/api/demo")
def demo():
    material = Material.default()
    p = uniaxial(material,np.linspace(0,.5,41))
    # Deterministic, explicitly synthetic. Never pretend these are measured data.
    rng = np.random.default_rng(4)
    data = Dataset(p["log_strain"],p["stress"]+rng.normal(0,.003,41),
                   p["log_J"]+rng.normal(0,2e-5,41),"Synthetic demonstration")
    return {"data":data.payload(),"truth":asdict(material),"synthetic":True}


@app.post("/api/import")
def import_file(body: ImportRequest):
    try: return read_table(**body.model_dump())
    except Exception as exc: raise HTTPException(422,str(exc)) from exc


@app.post("/api/normalize")
def normalize_file(body: NormalizeRequest):
    try: return normalize(**body.model_dump()).payload()
    except Exception as exc: raise HTTPException(422,str(exc)) from exc


@app.post("/api/fit")
def fit_request(body: FitRequest):
    try:
        material = Material(**body.material.model_dump())
        data = Dataset(**body.data.model_dump())
        objective = Objective(**body.objective)
    except (ValueError,TypeError,KeyError) as exc: raise HTTPException(422,str(exc)) from exc
    return submit("fit",body.model_dump(),lambda progress,cancel:fit(
        data,material,objective,body.starts,body.max_nfev,body.loss,body.seed,body.bounds,
        progress,cancel,body.tradeoff,body.initialization,body.pool_size))


@app.post("/api/fem")
def fem_request(body: FEMRequest):
    try: material = Material(**body.material.model_dump())
    except (ValueError,KeyError) as exc: raise HTTPException(422,str(exc)) from exc
    def calculate(progress,cancel):
        result=cube_test(material,body.stretch,body.cells,body.steps,body.clamped,progress,cancel)
        if not body.clamped:
            stretches=np.array([r["stretch"] for r in result["records"]])
            point=uniaxial(material,np.log(stretches))
            result["analytic_comparison"]={
                "max_nominal_stress_error":float(np.max(abs(np.array([r["nominal_stress"] for r in result["records"]])-point["nominal_stress"]))),
                "max_log_J_error":float(np.max(abs(np.array([r["mean_log_J"] for r in result["records"]])-point["log_J"])))}
            result["stability_screen"]=acoustic_screen(material,np.array([np.diag(l) for l in point["stretch"]]))
        return result
    return submit("fem",body.model_dump(),calculate)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    if len(job_id)!=32 or any(c not in "0123456789abcdef" for c in job_id): raise HTTPException(404)
    with lock:
        if job_id in jobs: return {k:v for k,v in jobs[job_id].items() if k!="cancel"}
    directory = run_root/job_id
    if not (directory/"input.json").exists(): raise HTTPException(404)
    if (directory/"result.json").exists():
        result = json.loads((directory/"result.json").read_text(encoding="utf-8"))
        return {"status":"completed","kind":result["kind"],"result":result["result"]}
    if (directory/"status.json").exists(): return json.loads((directory/"status.json").read_text(encoding="utf-8"))
    return {"status":"interrupted","error":"Server stopped before the job completed. Restart from the saved configuration."}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    with lock:
        if job_id not in jobs: raise HTTPException(404)
        jobs[job_id]["cancel"].set()
    return {"requested":True,"note":"FEM cancellation is checked after the current load increment."}


@app.get("/api/jobs/{job_id}/export")
def export_job(job_id: str, selected: int | None=Query(default=None,ge=0), download: bool=False):
    state = job_status(job_id)
    if state["status"]!="completed": raise HTTPException(409,"Job has not completed")
    output=json.loads((run_root/job_id/"result.json").read_text(encoding="utf-8"))
    if selected is not None:
        if output["kind"]!="fit" or selected>=len(output["result"]["candidates"]):
            raise HTTPException(422,"Invalid selected candidate")
        output["selected_candidate"]=selected
    if download:
        return JSONResponse(output,headers={"Content-Disposition":f'attachment; filename="hyperfit-{job_id}.json"'})
    return output


frontend = Path(__file__).resolve().parent/"frontend"
if frontend.exists(): app.mount("/",StaticFiles(directory=frontend,html=True),name="frontend")
