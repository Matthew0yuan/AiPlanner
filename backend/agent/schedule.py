from planner_core.planner import PlannerService
from planner_core.providers import create_provider_from_env


def schedule(tasks: list[dict], work_hours: str = "9-18", target_date: str | None = None) -> list[dict]:
    planner = PlannerService(create_provider_from_env())
    return planner.schedule(tasks, work_hours, target_date)
