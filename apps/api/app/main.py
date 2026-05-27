from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.routers import analysis, backtests, health, ingestion, matches, model, prematch, research, simulation, value
from app.ui import HOME_HTML


app = FastAPI(
    title="Football Predictor 2026 API",
    version="0.1.0",
    description="Demo API scaffold for World Cup 2026 football prediction.",
)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return HOME_HTML


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(matches.router)
app.include_router(analysis.router)
app.include_router(value.router)
app.include_router(backtests.router)
app.include_router(simulation.router)
app.include_router(model.router)
app.include_router(ingestion.router)
app.include_router(prematch.router)
app.include_router(research.router)
