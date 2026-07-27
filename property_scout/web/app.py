"""FastAPI web UI - a single page, no build step.

Search runs in a background thread; the browser polls ``/api/status`` for live
progress ("querying Property24 …") and then renders the results table and the
export download links. Plain HTML + vanilla JS (see templates/index.html).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import load_config
from ..logging_config import setup_logging
from ..pipeline import Pipeline, RunResult
from ..exporters import export_docx, export_xlsx, write_json_report

app = FastAPI(title="Property Scout")

_config = load_config()
setup_logging(_config.log_path)
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@dataclass
class Job:
    id: str
    events: List[dict] = field(default_factory=list)
    done: bool = False
    error: Optional[str] = None
    result: Optional[RunResult] = None
    files: Dict[str, str] = field(default_factory=dict)


_JOBS: Dict[str, Job] = {}


def _listing_rows(result: RunResult) -> List[dict]:
    rows = []
    for section, listings in (("Qualifying", result.main),
                              ("Age Unconfirmed", result.age_unconfirmed),
                              ("Needs Verification", result.needs_verification)):
        for l in listings:
            rows.append({
                "section": section,
                "source": l.source,
                "agency": l.agency_name,
                "agent": l.agent_name or "",
                "phone": l.agent_phone or "",
                "email": l.agent_email or "",
                "title": l.title,
                "type": l.property_type,
                "suburb": l.suburb,
                "rent": l.monthly_rent,
                "vat": l.rent_basis,
                "size": l.size_sqm,
                "size_conf": l.size_confidence,
                "dom": l.days_on_market,
                "age_conf": l.age_confidence,
                "live": l.last_seen.strftime("%Y-%m-%d") if l.last_seen else "",
                "flags": ";".join(l.flags),
                "url": l.url,
            })
    return rows


def _run_job(job: Job, params: dict) -> None:
    def progress(event: str, data: dict):
        job.events.append({"event": event, **data})

    try:
        config = load_config()
        pipeline = Pipeline(config)
        result = pipeline.run(
            area=params["area"],
            max_rent=params.get("max_rent"),
            min_size_sqm=params.get("min_size"),
            radius_km=params.get("radius"),
            include_residential=params.get("include_residential", False),
            only_sources=params.get("sources"),
            progress=progress,
        )
        job.result = result
        out = config.export_path
        job.files = {
            "docx": str(export_docx(result, out)),
            "xlsx": str(export_xlsx(result, out)),
            "json": str(write_json_report(result, out)),
        }
    except Exception as exc:  # noqa: BLE001
        job.error = repr(exc)
    finally:
        job.done = True


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _templates.TemplateResponse("index.html", {
        "request": request,
        "config": _config,
        "saved_areas": _config.saved_areas,
        "default_max_rent": _config.default_max_rent,
        "default_min_size": _config.default_min_size_sqm,
        "sources": list(_config.sources.keys()),
    })


@app.post("/api/search")
async def start_search(request: Request):
    body = await request.json()
    job = Job(id=uuid.uuid4().hex[:12])
    _JOBS[job.id] = job
    params = {
        "area": (body.get("area") or "").strip(),
        "max_rent": int(body["max_rent"]) if body.get("max_rent") else None,
        "min_size": int(body["min_size"]) if body.get("min_size") else None,
        "radius": int(body["radius"]) if body.get("radius") else None,
        "include_residential": bool(body.get("include_residential")),
        "sources": body.get("sources") or None,
    }
    if not params["area"]:
        return JSONResponse({"error": "area is required"}, status_code=400)
    threading.Thread(target=_run_job, args=(job, params), daemon=True).start()
    return {"job_id": job.id}


@app.get("/api/status/{job_id}")
def status(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "unknown job"}, status_code=404)
    payload = {
        "done": job.done,
        "error": job.error,
        "events": job.events,
    }
    if job.done and job.result is not None:
        r = job.result
        payload["summary"] = {
            "area": r.area,
            "qualifying": len(r.main),
            "age_unconfirmed": len(r.age_unconfirmed),
            "needs_verification": len(r.needs_verification),
            "dropped_since_last": len(r.dropped_since_last),
            "sources_blocked": r.sources_blocked,
        }
        payload["rows"] = _listing_rows(r)
        payload["report"] = r.report_dict()
        payload["files"] = {k: Path(v).name for k, v in job.files.items()}
    return payload


@app.get("/api/download/{job_id}/{kind}")
def download(job_id: str, kind: str):
    job = _JOBS.get(job_id)
    if not job or kind not in job.files:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = job.files[kind]
    return FileResponse(path, filename=Path(path).name)
