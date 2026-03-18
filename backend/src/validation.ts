import { z } from "zod";

import type { RemainingTask, Task, TimeBlock } from "./types";

const workHoursPattern = /^([01]?\d|2[0-3])-([01]?\d|2[0-3])$/;
const timePattern = /^(?:[01]\d|2[0-3]):[0-5]\d$/;

export function parseWorkHours(workHours: string): [number, number] {
  const match = workHours.match(workHoursPattern);
  if (!match) {
    throw new Error("work_hours must use the format H-H or HH-HH within 0-23");
  }

  const startHour = Number(match[1]);
  const endHour = Number(match[2]);
  if (startHour >= endHour) {
    throw new Error("work_hours must have a start hour earlier than the end hour");
  }

  return [startHour * 60, endHour * 60];
}

export function parseClockTime(value: string, fieldName = "time"): number {
  if (!timePattern.test(value)) {
    throw new Error(`${fieldName} must use the format HH:MM`);
  }

  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

export function validateTimeBlocks(
  blocks: TimeBlock[],
  workHours: string,
  currentTime?: string,
): TimeBlock[] {
  if (!blocks.length) {
    throw new Error("Expected at least one time block");
  }

  const [dayStart, dayEnd] = parseWorkHours(workHours);
  const currentMinutes = currentTime ? parseClockTime(currentTime, "current_time") : undefined;
  let previousEnd: number | undefined;

  for (const [index, block] of blocks.entries()) {
    if (!block.task_title.trim()) {
      throw new Error(`blocks[${index}].task_title cannot be empty`);
    }

    const startMinutes = parseClockTime(block.start, `blocks[${index}].start`);
    const endMinutes = parseClockTime(block.end, `blocks[${index}].end`);

    if (startMinutes >= endMinutes) {
      throw new Error(`blocks[${index}] must end after it starts`);
    }
    if (startMinutes < dayStart) {
      throw new Error(`blocks[${index}] starts before the work window`);
    }
    if (endMinutes > dayEnd) {
      throw new Error(`blocks[${index}] ends after the work window`);
    }
    if (currentMinutes !== undefined && startMinutes < currentMinutes) {
      throw new Error(`blocks[${index}] starts before current_time`);
    }
    if (previousEnd !== undefined && startMinutes < previousEnd) {
      throw new Error(`blocks[${index}] overlaps a previous block`);
    }

    previousEnd = endMinutes;
  }

  return blocks;
}

export const taskSchema: z.ZodType<Task> = z.object({
  id: z.string().optional(),
  title: z.string().min(1),
  estimate_minutes: z.number().int().min(15).max(240),
  energy: z.enum(["low", "med", "high"]),
  dependencies: z.array(z.string()),
  required_materials: z.array(z.string()),
  acceptance_criteria: z.string().min(1),
  risk_blockers: z.array(z.string()),
});

export const remainingTaskSchema: z.ZodType<RemainingTask> = z.object({
  task_title: z.string().min(1),
  mode: z.enum(["deep", "light", "admin"]),
});

export const timeBlockSchema: z.ZodType<TimeBlock> = z.object({
  task_title: z.string().min(1),
  start: z.string(),
  end: z.string(),
  mode: z.enum(["deep", "light", "admin", "break"]),
});

export const decomposeRequestSchema = z.object({
  goal: z.string().min(1),
  work_hours: z.string().default("9-18"),
  deadline: z.string().nullable().optional(),
});

export const scheduleRequestSchema = z.object({
  tasks: z.array(taskSchema).min(1),
  work_hours: z.string().default("9-18"),
  date: z.string().nullable().optional(),
});

export const rescheduleRequestSchema = z.object({
  remaining_tasks: z.array(remainingTaskSchema).min(1),
  current_time: z.string(),
  work_hours: z.string().default("9-18"),
  state_signal: z.record(z.any()).nullable().optional(),
});

export function normalizeWorkHours(workHours: string): string {
  parseWorkHours(workHours);
  return workHours;
}

export function normalizeCurrentTime(currentTime: string): string {
  parseClockTime(currentTime, "current_time");
  return currentTime;
}
