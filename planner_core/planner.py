import json
import re
import uuid
from datetime import date

from planner_core.prompts import (
    DECOMPOSE_SYSTEM_PROMPT,
    RESCHEDULE_SYSTEM_PROMPT,
    SCHEDULE_SYSTEM_PROMPT,
)
from planner_core.providers import TextProvider
from planner_core.validation import parse_work_hours, validate_time_blocks


GENERIC_CODING_KEYWORDS = {"code", "coding", "programming", "development", "dev"}
GENERIC_FILLER_WORDS = {
    "a",
    "an",
    "complete",
    "do",
    "finish",
    "just",
    "my",
    "need",
    "some",
    "the",
    "to",
    "today",
    "work",
    "on",
}


class PlannerService:
    def __init__(self, provider: TextProvider):
        self.provider = provider

    def decompose(self, goal: str, work_hours: str = "9-18", deadline: str | None = None) -> list[dict]:
        if self._is_generic_coding_goal(goal):
            return [self._build_generic_coding_task(work_hours)]

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
                if not 1 <= len(tasks) <= 10:
                    raise ValueError(f"Expected 1-10 tasks, got {len(tasks)}")
                return [self._validate_task(task) for task in tasks]
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                if attempt == 1:
                    raise ValueError(f"Agent returned invalid JSON after 2 attempts: {exc}\nRaw output: {raw}")

        return []

    @staticmethod
    def _is_generic_coding_goal(goal: str) -> bool:
        words = [
            word
            for word in re.findall(r"[a-z0-9]+", goal.lower())
            if word not in GENERIC_FILLER_WORDS
        ]
        if not words:
            return False
        return any(word in GENERIC_CODING_KEYWORDS for word in words) and all(
            word in GENERIC_CODING_KEYWORDS for word in words
        )

    @staticmethod
    def _build_generic_coding_task(work_hours: str) -> dict:
        start_minutes, end_minutes = parse_work_hours(work_hours)
        estimate_minutes = max(15, min(end_minutes - start_minutes, 240))
        return {
            "id": str(uuid.uuid4()),
            "title": "Coding",
            "estimate_minutes": estimate_minutes,
            "energy": "high",
            "dependencies": [],
            "required_materials": [],
            "acceptance_criteria": "Spend the scheduled block actively coding on the task at hand.",
            "risk_blockers": [],
        }

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
