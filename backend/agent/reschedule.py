import json
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are a dynamic rescheduler. Given the remaining tasks and CURRENT time, output a revised schedule for the rest of the day based on the time given.

You MUST output ONLY a valid JSON array. No prose, no markdown, no code fences.

Each block must have exactly these fields:
{
  "task_title": string,
  "start": "HH:MM",
  "end": "HH:MM",
  "mode": "deep" | "light" | "admin" | "break"
}

Only output blocks from current_time onwards — do not touch past blocks.

If state_signal is provided, apply these rules:
- gaze.attention_on_screen = false AND off_screen_duration_sec > 30: insert a 5-min "Refocus Break" before the next deep block
- fatigue_risk > 0.7: shift high-energy tasks later, insert a recovery block
- restlessness > 0.7: split next deep block into shorter chunks + insert 2-min resets

Output ONLY the JSON array."""


def reschedule(
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
