import json
from datetime import date
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are a daily schedule optimizer. Given a list of tasks and available time windows, output a time-blocked schedule.



Rules:
- Place high-energy tasks in morning slots (before 13:00)
- If work time < 4 hours, work block will be 25 mins
- Deep work blocks: 50-90 minutes
- Insert a 10-minute break after every 50-90 min deep block (use mode "break", task_title "Break")
- Light/admin tasks can go in afternoon
- Never schedule past the available end time
- Cover all tasks — do not skip any
- Output ONLY the JSON array.

Before Breakdown task:
- Think about what is an actual progress，milestone
- if you don't know about the task, just allocate times for the task and no need to actually break it down
- e.g. if task is vague says complete XXX just allocate XXX 25-120 total times

You MUST output ONLY a valid JSON array of time blocks. No prose, no markdown, no code fences.

Each block must have exactly these fields:
{
  "task_title": string,
  "start": "HH:MM",
  "end": "HH:MM",
  "mode": "deep" | "light" | "admin" | "break"
}
"""


def schedule(tasks: list[dict], work_hours: str = "9-18", target_date: str | None = None) -> list[dict]:
    if not target_date:
        target_date = date.today().isoformat()

    start_h, end_h = work_hours.split("-")
    user_message = (
        f"Date: {target_date}\n"
        f"Available hours: {work_hours} (from {start_h}:00 to {end_h}:00)\n"
        f"Tasks to schedule:\n{json.dumps(tasks, indent=2)}"
    )

    for attempt in range(2):
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
            ),
        )
        raw = response.text.strip()

        try:
            blocks = json.loads(raw)
            if not isinstance(blocks, list):
                raise ValueError("Expected a JSON array")
            validated = [_validate_block(b) for b in blocks]
            return validated
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == 1:
                raise ValueError(f"Agent returned invalid JSON after 2 attempts: {e}\nRaw: {raw}")

    return []


def _validate_block(raw: dict) -> dict:
    required = {"task_title": str, "start": str, "end": str, "mode": str}
    for field, t in required.items():
        if field not in raw:
            raise KeyError(f"Missing field: {field}")
        if not isinstance(raw[field], t):
            raise ValueError(f"Field '{field}' must be {t.__name__}")
    if raw["mode"] not in ("deep", "light", "admin", "break"):
        raise ValueError(f"Invalid mode: {raw['mode']}")
    return {k: raw[k] for k in required}
