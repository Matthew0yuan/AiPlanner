from pydantic import BaseModel, Field, model_validator

from planner_core.models import RemainingTask, Task, TimeBlock, WorkHoursMixin
from planner_core.validation import parse_clock_time


class DecomposeRequest(WorkHoursMixin):
    goal: str
    deadline: str | None = None

    @model_validator(mode="after")
    def validate_goal(self):
        if not self.goal.strip():
            raise ValueError("goal cannot be empty")
        return self


class DecomposeResponse(BaseModel):
    tasks: list[Task]


class ScheduleRequest(WorkHoursMixin):
    tasks: list[Task] = Field(min_length=1)
    date: str | None = None


class ScheduleResponse(BaseModel):
    blocks: list[TimeBlock]


class RescheduleRequest(WorkHoursMixin):
    remaining_tasks: list[RemainingTask] = Field(min_length=1)
    current_time: str
    state_signal: dict | None = None

    @model_validator(mode="after")
    def validate_current_time(self):
        parse_clock_time(self.current_time, "current_time")
        return self


class RescheduleResponse(BaseModel):
    blocks: list[TimeBlock]
