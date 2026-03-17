from planner_core.planner import PlannerService
from planner_core.providers import create_provider_from_env


def decompose(goal: str, work_hours: str = "9-18", deadline: str | None = None) -> list[dict]:
    planner = PlannerService(create_provider_from_env())
    return planner.decompose(goal, work_hours, deadline)
