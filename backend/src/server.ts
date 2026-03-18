import "dotenv/config";

import cors from "cors";
import express, { type Request, type Response } from "express";
import { ZodError } from "zod";

import { PlannerService } from "./planner";
import { createProviderFromEnv } from "./providers";
import {
  decomposeRequestSchema,
  normalizeCurrentTime,
  normalizeWorkHours,
  rescheduleRequestSchema,
  scheduleRequestSchema,
} from "./validation";

const app = express();
const port = Number(process.env.PORT ?? 8000);

app.use(cors({
  origin: ["http://localhost:5173", "http://localhost:3000"],
}));
app.use(express.json());

function getPlanner(): PlannerService {
  return new PlannerService(createProviderFromEnv());
}

function sendError(res: Response, status: number, detail: string): void {
  res.status(status).json({ detail });
}

app.post("/agent/decompose", async (req: Request, res: Response) => {
  try {
    const body = decomposeRequestSchema.parse(req.body);
    const tasks = await getPlanner().decompose(
      body.goal.trim(),
      normalizeWorkHours(body.work_hours),
      body.deadline ?? undefined,
    );
    res.json({ tasks });
  } catch (error) {
    if (error instanceof ZodError) {
      return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
    }
    return sendError(res, 502, (error as Error).message);
  }
});

app.post("/agent/schedule", async (req: Request, res: Response) => {
  try {
    const body = scheduleRequestSchema.parse(req.body);
    const blocks = await getPlanner().schedule(
      body.tasks,
      normalizeWorkHours(body.work_hours),
      body.date ?? undefined,
    );
    res.json({ blocks });
  } catch (error) {
    if (error instanceof ZodError) {
      return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
    }
    return sendError(res, 502, (error as Error).message);
  }
});

app.post("/agent/reschedule", async (req: Request, res: Response) => {
  try {
    const body = rescheduleRequestSchema.parse(req.body);
    const blocks = await getPlanner().reschedule(
      body.remaining_tasks,
      normalizeCurrentTime(body.current_time),
      normalizeWorkHours(body.work_hours),
      body.state_signal ?? undefined,
    );
    res.json({ blocks });
  } catch (error) {
    if (error instanceof ZodError) {
      return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
    }
    return sendError(res, 502, (error as Error).message);
  }
});

app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok" });
});

app.listen(port, () => {
  console.log(`AiPlanner backend listening on http://localhost:${port}`);
});
