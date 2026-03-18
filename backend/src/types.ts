export type ProviderName = "openai" | "claude" | "gemini";

export interface Task {
  id?: string;
  title: string;
  estimate_minutes: number;
  energy: "low" | "med" | "high";
  dependencies: string[];
  required_materials: string[];
  acceptance_criteria: string;
  risk_blockers: string[];
}

export interface RemainingTask {
  task_title: string;
  mode: "deep" | "light" | "admin";
}

export interface TimeBlock {
  task_title: string;
  start: string;
  end: string;
  mode: "deep" | "light" | "admin" | "break";
}
