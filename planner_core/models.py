from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from planner_core.validation import parse_clock_time, parse_work_hours


class WorkHoursMixin(BaseModel):
    work_hours: str = "9-18"

    @model_validator(mode="after")
    def validate_work_hours(self):
        parse_work_hours(self.work_hours)
        return self


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    title: str = Field(min_length=1)
    estimate_minutes: int = Field(ge=15, le=240)
    energy: Literal["low", "med", "high"]
    dependencies: list[str] = Field(default_factory=list)
    required_materials: list[str] = Field(default_factory=list)
    acceptance_criteria: str = Field(min_length=1)
    risk_blockers: list[str] = Field(default_factory=list)


class RemainingTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_title: str = Field(min_length=1)
    mode: Literal["deep", "light", "admin"]


class TimeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_title: str = Field(min_length=1)
    start: str
    end: str
    mode: Literal["deep", "light", "admin", "break"]

    @model_validator(mode="after")
    def validate_times(self):
        start_minutes = parse_clock_time(self.start, "start")
        end_minutes = parse_clock_time(self.end, "end")
        if start_minutes >= end_minutes:
            raise ValueError("end must be later than start")
        return self
