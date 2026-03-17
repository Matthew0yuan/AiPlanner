from planner_core.planner import PlannerService
from planner_core.providers import create_provider_from_env


def reschedule(
    remaining_tasks: list[dict],
    current_time: str,
    work_hours: str = "9-18",
    state_signal: dict | None = None,
) -> list[dict]:
    planner = PlannerService(create_provider_from_env())
    return planner.reschedule(remaining_tasks, current_time, work_hours, state_signal)
