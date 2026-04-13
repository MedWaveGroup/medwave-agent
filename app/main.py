"""MedWave Ad Tracker — FastAPI application with hourly auto-refresh."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.tracker import refresh_data, get_cached_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run initial data fetch on startup
    await refresh_data()
    # Schedule hourly refresh
    scheduler.add_job(refresh_data, "interval", hours=1, id="hourly_refresh")
    scheduler.start()
    logger.info("Scheduler started — refreshing every 1 hour")
    yield
    scheduler.shutdown()


app = FastAPI(title="MedWave Ad Tracker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = get_cached_data()
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})


@app.get("/api/data")
async def api_data():
    return get_cached_data()


@app.post("/api/refresh")
async def api_refresh():
    data = await refresh_data()
    return {"status": "ok", "last_updated": data.get("last_updated")}
