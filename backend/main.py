from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent.decompose import decompose
from agent.schedule import schedule
from agent.reschedule import reschedule

app = FastAPI(title="AiPlanner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Decompose ---

class DecomposeRequest(BaseModel):
    goal: str
    work_hours: str = "9-18"
    deadline: str | None = None


class DecomposeResponse(BaseModel):
    tasks: list[dict]


@app.post("/agent/decompose", response_model=DecomposeResponse)
def decompose_goal(req: DecomposeRequest):
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="goal cannot be empty")
    try:
        tasks = decompose(req.goal, req.work_hours, req.deadline)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return DecomposeResponse(tasks=tasks)


# --- Schedule ---

class ScheduleRequest(BaseModel):
    tasks: list[dict]
    work_hours: str = "9-18"
    date: str | None = None


class ScheduleResponse(BaseModel):
    blocks: list[dict]


@app.post("/agent/schedule", response_model=ScheduleResponse)
def schedule_day(req: ScheduleRequest):
    if not req.tasks:
        raise HTTPException(status_code=400, detail="tasks cannot be empty")
    try:
        blocks = schedule(req.tasks, req.work_hours, req.date)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ScheduleResponse(blocks=blocks)


# --- Reschedule ---

class RescheduleRequest(BaseModel):
    remaining_tasks: list[dict]
    current_time: str
    work_hours: str = "9-18"
    state_signal: dict | None = None


class RescheduleResponse(BaseModel):
    blocks: list[dict]


@app.post("/agent/reschedule", response_model=RescheduleResponse)
def reschedule_day(req: RescheduleRequest):
    if not req.remaining_tasks:
        raise HTTPException(status_code=400, detail="remaining_tasks cannot be empty")
    try:
        blocks = reschedule(req.remaining_tasks, req.current_time, req.work_hours, req.state_signal)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return RescheduleResponse(blocks=blocks)


# --- Health ---

@app.get("/health")
def health():
    return {"status": "ok"}
