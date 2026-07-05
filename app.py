"""
FastAPI backend for the Pipeline Memory UI.

Endpoints:
  GET  /              -> serve the UI (index.html)
  POST /investigate   -> run recall() against a new symptom, return JSON
  POST /forget        -> forget() a pipeline's entire memory
  GET  /pipelines     -> list known pipelines from pipelines.json

FastAPI is already installed as part of cognee's dependency tree, so no
extra pip install needed.

Run:
    python app.py
Then open http://localhost:8000 in your browser.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cognee_layer.config import configure_cognee, dataset_for_pipeline, all_dataset_names
from cognee_layer.query import investigate, format_recall_result

DATA_DIR = Path(__file__).parent / "data"

app = FastAPI(title="Pipeline Memory")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class InvestigateRequest(BaseModel):
    symptom: str


class ForgetRequest(BaseModel):
    pipeline: str


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "ui" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/pipelines")
async def get_pipelines():
    with open(DATA_DIR / "pipelines.json") as f:
        pipelines = json.load(f)
    return JSONResponse(pipelines)


@app.post("/investigate")
async def investigate_endpoint(req: InvestigateRequest):
    if not req.symptom.strip():
        return JSONResponse({"error": "symptom cannot be empty"}, status_code=400)
    try:
        result = await investigate(req.symptom)
        return JSONResponse({"symptom": req.symptom, "result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/forget")
async def forget_endpoint(req: ForgetRequest):
    cognee = configure_cognee()
    dataset = dataset_for_pipeline(req.pipeline)
    try:
        await cognee.forget(dataset=dataset)
        return JSONResponse({"status": "ok", "message": f"Memory for '{req.pipeline}' pipeline has been pruned."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
