# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import asdict
import time
from fastapi.testclient import TestClient
from hyperfit import api
from hyperfit.models import Material


def wait(client,job_id):
    until=time.monotonic()+20
    while time.monotonic()<until:
        state=client.get(f"/api/jobs/{job_id}").json()
        if state["status"] not in ("queued","running"):return state
        time.sleep(.025)
    raise AssertionError("Local job did not finish within 20 seconds")


def test_complete_fit_export_reconnect_and_fem(tmp_path,monkeypatch):
    monkeypatch.setattr(api,"run_root",tmp_path)
    client=TestClient(api.app)
    assert client.get("/").status_code==200
    demo=client.get("/api/demo").json()
    request={"material":asdict(Material.default()),"data":demo["data"],"starts":1,"max_nfev":30}
    response=client.post("/api/fit",json=request)
    assert response.status_code==200
    job_id=response.json()["job_id"];state=wait(client,job_id)
    assert state["status"]=="completed",state
    assert state["result"]["qualified_candidate_found"]
    exported=client.get(f"/api/jobs/{job_id}/export").json()
    assert exported["config"]==api.FitRequest(**request).model_dump()
    assert "models.py" in exported["source_sha256"]
    assert len(exported["configuration_sha256"])==64
    download=client.get(f"/api/jobs/{job_id}/export?download=true&selected=0")
    assert "attachment" in download.headers["content-disposition"]
    assert download.json()["selected_candidate"]==0
    assert client.get(f"/api/jobs/{job_id}/export?selected=999").status_code==422
    with api.lock:api.jobs.pop(job_id)
    assert client.get(f"/api/jobs/{job_id}").json()["status"]=="completed"
    fe=client.post("/api/fem",json={"material":asdict(Material.default()),"cells":1,"steps":3}).json()
    state=wait(client,fe["job_id"])
    assert state["status"]=="completed",state
    assert state["result"]["analytic_comparison"]["max_nominal_stress_error"]<1e-7


def test_invalid_input_returns_error_without_scheduling():
    client=TestClient(api.app)
    bad={"material":asdict(Material.default()),"data":{"log_strain":[0,0,.2,.3],"stress":[0,1,2,3],"log_J":[0,0,0,0]}}
    assert client.post("/api/fit",json=bad).status_code==422
    assert client.get("/api/jobs/not-a-job").status_code==404
    assert client.post("/api/fem",json={"material":asdict(Material.default()),"cells":100}).status_code==422
