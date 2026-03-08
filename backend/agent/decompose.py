import json
import uuid
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are a task decomposition engine. Your job is to break a user's goal into concrete, actionable tasks.

You MUST output ONLY a valid JSON array. No prose, no markdown, no code fences. Just the raw JSON array.

Each task object MUST have exactly these fields:
{
  "title": string,
  "estimate_minutes": integer,
  "energy": "low" | "med" | "high",
  "dependencies": [string],
  "required_materials": [string],
  "acceptance_criteria": string,
  "risk_blockers": [string]
}

Rules:
- Break the goal into 3-10 tasks (never fewer than 3, never more than 10)
- estimate_minutes must be a realistic integer (minimum 15, maximum 240 per task)
- energy: "high" = requires deep focus/creativity, "med" = moderate concentration, "low" = routine/admin
- dependencies: list task titles this task depends on (empty array if none)
- required_materials: tools, accounts, files, credentials needed (empty array if none)
- acceptance_criteria: one clear sentence describing what "done" looks like
- risk_blockers: specific things that could prevent completion (empty array if none)

If the goal is too vague, make reasonable assumptions and decompose anyway.
Output ONLY the JSON array. Nothing else."""


def decompose(goal: str, work_hours: str = "9-18", deadline: str | None = None) -> list[dict]:
    user_message = f"Goal: {goal}"
    if deadline:
        user_message += f"\nDeadline: {deadline}"
    if work_hours:
        user_message += f"\nWork hours: {work_hours}"

    for attempt in range(2):
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
            ),
        )
        raw = response.text.strip()

        try:
            tasks = json.loads(raw)
            if not isinstance(tasks, list):
                raise ValueError("Expected a JSON array")
            validated = [_validate_task(t) for t in tasks]
            return validated
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 1:
                raise ValueError(f"Agent returned invalid JSON after 2 attempts: {e}\nRaw output: {raw}")
            # retry on first failure

    return []  # unreachable, satisfies type checker


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
        **{k: raw[k] for k in required_fields},
    }
