"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
require("dotenv/config");
const cors_1 = __importDefault(require("cors"));
const express_1 = __importDefault(require("express"));
const zod_1 = require("zod");
const planner_1 = require("./planner");
const providers_1 = require("./providers");
const validation_1 = require("./validation");
const app = (0, express_1.default)();
const port = Number(process.env.PORT ?? 8000);
app.use((0, cors_1.default)({
    origin: ["http://localhost:5173", "http://localhost:3000"],
}));
app.use(express_1.default.json());
function getPlanner() {
    return new planner_1.PlannerService((0, providers_1.createProviderFromEnv)());
}
function sendError(res, status, detail) {
    res.status(status).json({ detail });
}
app.post("/agent/decompose", async (req, res) => {
    try {
        const body = validation_1.decomposeRequestSchema.parse(req.body);
        const tasks = await getPlanner().decompose(body.goal.trim(), (0, validation_1.normalizeWorkHours)(body.work_hours), body.deadline ?? undefined);
        res.json({ tasks });
    }
    catch (error) {
        if (error instanceof zod_1.ZodError) {
            return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
        }
        return sendError(res, 502, error.message);
    }
});
app.post("/agent/schedule", async (req, res) => {
    try {
        const body = validation_1.scheduleRequestSchema.parse(req.body);
        const blocks = await getPlanner().schedule(body.tasks, (0, validation_1.normalizeWorkHours)(body.work_hours), body.date ?? undefined);
        res.json({ blocks });
    }
    catch (error) {
        if (error instanceof zod_1.ZodError) {
            return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
        }
        return sendError(res, 502, error.message);
    }
});
app.post("/agent/reschedule", async (req, res) => {
    try {
        const body = validation_1.rescheduleRequestSchema.parse(req.body);
        const blocks = await getPlanner().reschedule(body.remaining_tasks, (0, validation_1.normalizeCurrentTime)(body.current_time), (0, validation_1.normalizeWorkHours)(body.work_hours), body.state_signal ?? undefined);
        res.json({ blocks });
    }
    catch (error) {
        if (error instanceof zod_1.ZodError) {
            return sendError(res, 400, error.issues[0]?.message ?? "Invalid request");
        }
        return sendError(res, 502, error.message);
    }
});
app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
});
app.listen(port, () => {
    console.log(`AiPlanner backend listening on http://localhost:${port}`);
});
