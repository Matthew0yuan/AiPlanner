import json
import uuid
from datetime import date

from planner_core.prompts import (
    DECOMPOSE_SYSTEM_PROMPT,
    RESCHEDULE_SYSTEM_PROMPT,
    SCHEDULE_SYSTEM_PROMPT,
)
from planner_core.providers import TextProvider
from planner_core.validation import validate_time_blocks


class PlannerService:
    def __init__(self, provider: TextProvider):
        self.provider = provider

    def decompose(self, goal: str, work_hours: str = "9-18", deadline: str | None = None) -> list[dict]:
        user_message = f"Goal: {goal}"
        if deadline:
            user_message += f"\nDeadline: {deadline}"
        if work_hours:
            user_message += f"\nWork hours: {work_hours}"

        for attempt in range(2):
            raw = self.provider.generate_text(DECOMPOSE_SYSTEM_PROMPT, user_message, temperature=0.3)
            try:
                tasks = json.loads(raw)
                if not isinstance(tasks, list):
                    raise ValueError("Expected a JSON array")
                if not 3 <= len(tasks) <= 10:
                    raise ValueError(f"Expected 3-10 tasks, got {len(tasks)}")
                return [self._validate_task(task) for task in tasks]
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                if attempt == 1:
                    raise ValueError(f"Agent returned invalid JSON after 2 attempts: {exc}\nRaw output: {raw}")

        return []

    def schedule(self, tasks: list[dict], work_hours: str = "9-18", target_date: str | None = None) -> list[dict]:
        if not target_date:
            target_date = date.today().isoformat()

        start_h, end_h = work_hours.split("-")
        user_message = (
            f"Date: {target_date}\n"
            f"Available hours: {work_hours} (from {start_h}:00 to {end_h}:00)\n"
            f"Tasks to schedule:\n{json.dumps(tasks, indent=2)}"
        )

        for attempt in range(2):
            raw = self.provider.generate_text(SCHEDULE_SYSTEM_PROMPT, user_message, temperature=0.2)
            try:
                blocks = json.loads(raw)
                if not isinstance(blocks, list):
                    raise ValueError("Expected a JSON array")
                validated = [self._validate_block(block) for block in blocks]
                return validate_time_blocks(validated, work_hours)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                if attempt == 1:
                    raise ValueError(f"Agent returned invalid JSON after 2 attempts: {exc}\nRaw: {raw}")

        return []

    def reschedule(
        self,
        remaining_tasks: list[dict],
        current_time: str,
        work_hours: str = "9-18",
        state_signal: dict | None = None,
    ) -> list[dict]:
        _, end_h = work_hours.split("-")
        user_message = (
            f"Current time: {current_time}\n"
            f"Available until: {end_h}:00\n"
            f"Remaining tasks:\n{json.dumps(remaining_tasks, indent=2)}"
        )
        if state_signal:
            user_message += f"\nState signal:\n{json.dumps(state_signal, indent=2)}"

        for attempt in range(2):
            raw = self.provider.generate_text(RESCHEDULE_SYSTEM_PROMPT, user_message, temperature=0.2)
            try:
                blocks = json.loads(raw)
                if not isinstance(blocks, list):
                    raise ValueError("Expected a JSON array")
                validated = [self._validate_block(block) for block in blocks]
                return validate_time_blocks(validated, work_hours, current_time=current_time)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                if attempt == 1:
                    raise ValueError(f"Agent returned invalid JSON after 2 attempts: {exc}\nRaw: {raw}")

        return []

    @staticmethod
    def _validate_task(raw: dict) -> dict:
        required_fields = {
            "title": str,
            "estimate_minutes": int,
            "energy": str,
            "dependencies": list,
            "required_materials": list,
            "acceptance_criteria": str,
            "risk_blockers": list,
        }
        for field, expected_type in required_fields.items():
            if field not in raw:
                raise KeyError(f"Missing field: {field}")
            if not isinstance(raw[field], expected_type):
                raise ValueError(f"Field '{field}' must be {expected_type.__name__}")

        if raw["energy"] not in ("low", "med", "high"):
            raise ValueError(f"energy must be low/med/high, got: {raw['energy']}")
        if not (15 <= raw["estimate_minutes"] <= 240):
            raise ValueError(f"estimate_minutes out of range: {raw['estimate_minutes']}")

        return {
            "id": str(uuid.uuid4()),
            **{key: raw[key] for key in required_fields},
        }

    @staticmethod
    def _validate_block(raw: dict) -> dict:
        required = {"task_title": str, "start": str, "end": str, "mode": str}
        for field, expected_type in required.items():
            if field not in raw:
                raise KeyError(f"Missing field: {field}")
            if not isinstance(raw[field], expected_type):
                raise ValueError(f"Field '{field}' must be {expected_type.__name__}")
        if raw["mode"] not in ("deep", "light", "admin", "break"):
            raise ValueError(f"Invalid mode: {raw['mode']}")
        return {key: raw[key] for key in required}
