import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
for path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

load_dotenv()

from agent.decompose import decompose
from agent.schedule import schedule
from agent.reschedule import reschedule
from models import (
    DecomposeRequest,
    DecomposeResponse,
    RescheduleRequest,
    RescheduleResponse,
    ScheduleRequest,
    ScheduleResponse,
)

app = FastAPI(title="AiPlanner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/agent/decompose", response_model=DecomposeResponse)
def decompose_goal(req: DecomposeRequest):
    try:
        tasks = decompose(req.goal, req.work_hours, req.deadline)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return DecomposeResponse(tasks=tasks)


@app.post("/agent/schedule", response_model=ScheduleResponse)
def schedule_day(req: ScheduleRequest):
    try:
        blocks = schedule([task.model_dump() for task in req.tasks], req.work_hours, req.date)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ScheduleResponse(blocks=blocks)


@app.post("/agent/reschedule", response_model=RescheduleResponse)
def reschedule_day(req: RescheduleRequest):
    try:
        blocks = reschedule(
            [task.model_dump() for task in req.remaining_tasks],
            req.current_time,
            req.work_hours,
            req.state_signal,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return RescheduleResponse(blocks=blocks)


# --- Health ---

@app.get("/health")
def health():
    return {"status": "ok"}
