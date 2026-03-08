# Core Data Schemas

## Task
```json
{
  "id": "uuid (string)",
  "title": "string",
  "estimate_minutes": "int",
  "energy": "low | med | high",
  "dependencies": ["task title or id (string)"],
  "required_materials": ["string"],
  "acceptance_criteria": "string — what 'done' looks like",
  "risk_blockers": ["string — things that could block this task"]
}
```

## Goal
```json
{
  "id": "uuid (string)",
  "description": "string — raw user input",
  "deadline": "ISO date string or null",
  "work_hours": "string — e.g. '9-18'",
  "created_at": "ISO datetime string"
}
```

## Plan (Time Block)
```json
{
  "id": "uuid (string)",
  "task_id": "string",
  "start": "ISO datetime string",
  "end": "ISO datetime string",
  "mode": "deep | light | admin",
  "state_signal": {
    "fatigue_risk": "float 0-1 (reserved for EEG)",
    "restlessness": "float 0-1 (reserved for EEG)",
    "gaze": {
      "attention_on_screen": "bool — true if camera detects user looking at screen",
      "off_screen_duration_sec": "float — seconds since gaze left screen (0 if on screen)",
      "confidence": "float 0-1 — gaze detection confidence"
    }
  }
}
```

## Log (Execution Record)
```json
{
  "id": "uuid (string)",
  "plan_id": "string",
  "task_id": "string",
  "started_at": "ISO datetime string",
  "ended_at": "ISO datetime string or null",
  "completion_pct": "int 0-100",
  "outcome": "done | skipped | delayed | blocked",
  "blocker_reason": "string or null"
}
```
