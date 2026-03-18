import { randomUUID } from "node:crypto";

import { DECOMPOSE_SYSTEM_PROMPT, RESCHEDULE_SYSTEM_PROMPT, SCHEDULE_SYSTEM_PROMPT } from "./prompts";
import type { RemainingTask, Task, TimeBlock } from "./types";
import { type TextProvider } from "./providers";
import { parseWorkHours, validateTimeBlocks } from "./validation";

const GENERIC_CODING_KEYWORDS = new Set(["code", "coding", "programming", "development", "dev"]);
const GENERIC_FILLER_WORDS = new Set([
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
]);

export class PlannerService {
  constructor(private readonly provider: TextProvider) {}

  async decompose(goal: string, workHours = "9-18", deadline?: string | null): Promise<Task[]> {
    if (this.isGenericCodingGoal(goal)) {
      return [this.buildGenericCodingTask(workHours)];
    }

    let userMessage = `Goal: ${goal}`;
    if (deadline) {
      userMessage += `\nDeadline: ${deadline}`;
    }
    if (workHours) {
      userMessage += `\nWork hours: ${workHours}`;
    }

    for (let attempt = 0; attempt < 2; attempt += 1) {
      const raw = await this.provider.generateText(DECOMPOSE_SYSTEM_PROMPT, userMessage, 0.3);
      try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
          throw new Error("Expected a JSON array");
        }
        if (parsed.length < 1 || parsed.length > 10) {
          throw new Error(`Expected 1-10 tasks, got ${parsed.length}`);
        }
        return parsed.map((task) => this.validateTask(task));
      } catch (error) {
        if (attempt === 1) {
          throw new Error(`Agent returned invalid JSON after 2 attempts: ${(error as Error).message}\nRaw output: ${raw}`);
        }
      }
    }

    return [];
  }

  private isGenericCodingGoal(goal: string): boolean {
    const words = (goal.toLowerCase().match(/[a-z0-9]+/g) ?? []).filter((word) => !GENERIC_FILLER_WORDS.has(word));
    if (!words.length) {
      return false;
    }
    return words.some((word) => GENERIC_CODING_KEYWORDS.has(word))
      && words.every((word) => GENERIC_CODING_KEYWORDS.has(word));
  }

  private buildGenericCodingTask(workHours: string): Task {
    const [dayStart, dayEnd] = parseWorkHours(workHours);
    const estimateMinutes = Math.max(15, Math.min(dayEnd - dayStart, 240));
    return {
      id: randomUUID(),
      title: "Coding",
      estimate_minutes: estimateMinutes,
      energy: "high",
      dependencies: [],
      required_materials: [],
      acceptance_criteria: "Spend the scheduled block actively coding on the task at hand.",
      risk_blockers: [],
    };
  }

  async schedule(tasks: Task[], workHours = "9-18", targetDate?: string | null): Promise<TimeBlock[]> {
    const date = targetDate || new Date().toISOString().slice(0, 10);
    const [startHour, endHour] = workHours.split("-");
    const userMessage = [
      `Date: ${date}`,
      `Available hours: ${workHours} (from ${startHour}:00 to ${endHour}:00)`,
      `Tasks to schedule:\n${JSON.stringify(tasks, null, 2)}`,
    ].join("\n");

    for (let attempt = 0; attempt < 2; attempt += 1) {
      const raw = await this.provider.generateText(SCHEDULE_SYSTEM_PROMPT, userMessage, 0.2);
      try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
          throw new Error("Expected a JSON array");
        }
        const validated = parsed.map((block) => this.validateBlock(block));
        return validateTimeBlocks(validated, workHours);
      } catch (error) {
        if (attempt === 1) {
          throw new Error(`Agent returned invalid JSON after 2 attempts: ${(error as Error).message}\nRaw: ${raw}`);
        }
      }
    }

    return [];
  }

  async reschedule(
    remainingTasks: RemainingTask[],
    currentTime: string,
    workHours = "9-18",
    stateSignal?: Record<string, unknown> | null,
  ): Promise<TimeBlock[]> {
    const [, endHour] = workHours.split("-");
    let userMessage = [
      `Current time: ${currentTime}`,
      `Available until: ${endHour}:00`,
      `Remaining tasks:\n${JSON.stringify(remainingTasks, null, 2)}`,
    ].join("\n");

    if (stateSignal) {
      userMessage += `\nState signal:\n${JSON.stringify(stateSignal, null, 2)}`;
    }

    for (let attempt = 0; attempt < 2; attempt += 1) {
      const raw = await this.provider.generateText(RESCHEDULE_SYSTEM_PROMPT, userMessage, 0.2);
      try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
          throw new Error("Expected a JSON array");
        }
        const validated = parsed.map((block) => this.validateBlock(block));
        return validateTimeBlocks(validated, workHours, currentTime);
      } catch (error) {
        if (attempt === 1) {
          throw new Error(`Agent returned invalid JSON after 2 attempts: ${(error as Error).message}\nRaw: ${raw}`);
        }
      }
    }

    return [];
  }

  private validateTask(raw: any): Task {
    const requiredFields = [
      "title",
      "estimate_minutes",
      "energy",
      "dependencies",
      "required_materials",
      "acceptance_criteria",
      "risk_blockers",
    ] as const;

    for (const field of requiredFields) {
      if (!(field in raw)) {
        throw new Error(`Missing field: ${field}`);
      }
    }

    if (!["low", "med", "high"].includes(raw.energy)) {
      throw new Error(`energy must be low/med/high, got: ${raw.energy}`);
    }
    if (!Number.isInteger(raw.estimate_minutes) || raw.estimate_minutes < 15 || raw.estimate_minutes > 240) {
      throw new Error(`estimate_minutes out of range: ${raw.estimate_minutes}`);
    }

    return {
      id: randomUUID(),
      title: String(raw.title),
      estimate_minutes: raw.estimate_minutes,
      energy: raw.energy,
      dependencies: Array.isArray(raw.dependencies) ? raw.dependencies.map(String) : [],
      required_materials: Array.isArray(raw.required_materials) ? raw.required_materials.map(String) : [],
      acceptance_criteria: String(raw.acceptance_criteria),
      risk_blockers: Array.isArray(raw.risk_blockers) ? raw.risk_blockers.map(String) : [],
    };
  }

  private validateBlock(raw: any): TimeBlock {
    const requiredFields = ["task_title", "start", "end", "mode"] as const;
    for (const field of requiredFields) {
      if (!(field in raw)) {
        throw new Error(`Missing field: ${field}`);
      }
    }
    if (!["deep", "light", "admin", "break"].includes(raw.mode)) {
      throw new Error(`Invalid mode: ${raw.mode}`);
    }
    return {
      task_title: String(raw.task_title),
      start: String(raw.start),
      end: String(raw.end),
      mode: raw.mode,
    };
  }
}
