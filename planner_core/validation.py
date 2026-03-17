import re


WORK_HOURS_PATTERN = re.compile(r"^([01]?\d|2[0-3])-([01]?\d|2[0-3])$")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def parse_work_hours(work_hours: str) -> tuple[int, int]:
    match = WORK_HOURS_PATTERN.fullmatch(work_hours)
    if not match:
        raise ValueError("work_hours must use the format H-H or HH-HH within 0-23")

    start_h = int(match.group(1))
    end_h = int(match.group(2))
    if start_h >= end_h:
        raise ValueError("work_hours must have a start hour earlier than the end hour")

    return start_h * 60, end_h * 60


def parse_clock_time(value: str, field_name: str = "time") -> int:
    if not TIME_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must use the format HH:MM")

    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def validate_time_blocks(
    blocks: list[dict],
    work_hours: str,
    current_time: str | None = None,
) -> list[dict]:
    if not blocks:
        raise ValueError("Expected at least one time block")

    day_start, day_end = parse_work_hours(work_hours)
    current_minutes = parse_clock_time(current_time, "current_time") if current_time else None
    previous_end = None

    for index, block in enumerate(blocks):
        task_title = block["task_title"].strip()
        if not task_title:
            raise ValueError(f"blocks[{index}].task_title cannot be empty")

        start_minutes = parse_clock_time(block["start"], f"blocks[{index}].start")
        end_minutes = parse_clock_time(block["end"], f"blocks[{index}].end")

        if start_minutes >= end_minutes:
            raise ValueError(f"blocks[{index}] must end after it starts")
        if start_minutes < day_start:
            raise ValueError(f"blocks[{index}] starts before the work window")
        if end_minutes > day_end:
            raise ValueError(f"blocks[{index}] ends after the work window")
        if current_minutes is not None and start_minutes < current_minutes:
            raise ValueError(f"blocks[{index}] starts before current_time")
        if previous_end is not None and start_minutes < previous_end:
            raise ValueError(f"blocks[{index}] overlaps a previous block")

        previous_end = end_minutes

    return blocks
