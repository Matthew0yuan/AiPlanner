"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.rescheduleRequestSchema = exports.scheduleRequestSchema = exports.decomposeRequestSchema = exports.timeBlockSchema = exports.remainingTaskSchema = exports.taskSchema = void 0;
exports.parseWorkHours = parseWorkHours;
exports.parseClockTime = parseClockTime;
exports.validateTimeBlocks = validateTimeBlocks;
exports.normalizeWorkHours = normalizeWorkHours;
exports.normalizeCurrentTime = normalizeCurrentTime;
const zod_1 = require("zod");
const workHoursPattern = /^([01]?\d|2[0-3])-([01]?\d|2[0-3])$/;
const timePattern = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
function parseWorkHours(workHours) {
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
function parseClockTime(value, fieldName = "time") {
    if (!timePattern.test(value)) {
        throw new Error(`${fieldName} must use the format HH:MM`);
    }
    const [hours, minutes] = value.split(":").map(Number);
    return hours * 60 + minutes;
}
function validateTimeBlocks(blocks, workHours, currentTime) {
    if (!blocks.length) {
        throw new Error("Expected at least one time block");
    }
    const [dayStart, dayEnd] = parseWorkHours(workHours);
    const currentMinutes = currentTime ? parseClockTime(currentTime, "current_time") : undefined;
    let previousEnd;
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
exports.taskSchema = zod_1.z.object({
    id: zod_1.z.string().optional(),
    title: zod_1.z.string().min(1),
    estimate_minutes: zod_1.z.number().int().min(15).max(240),
    energy: zod_1.z.enum(["low", "med", "high"]),
    dependencies: zod_1.z.array(zod_1.z.string()),
    required_materials: zod_1.z.array(zod_1.z.string()),
    acceptance_criteria: zod_1.z.string().min(1),
    risk_blockers: zod_1.z.array(zod_1.z.string()),
});
exports.remainingTaskSchema = zod_1.z.object({
    task_title: zod_1.z.string().min(1),
    mode: zod_1.z.enum(["deep", "light", "admin"]),
});
exports.timeBlockSchema = zod_1.z.object({
    task_title: zod_1.z.string().min(1),
    start: zod_1.z.string(),
    end: zod_1.z.string(),
    mode: zod_1.z.enum(["deep", "light", "admin", "break"]),
});
exports.decomposeRequestSchema = zod_1.z.object({
    goal: zod_1.z.string().min(1),
    work_hours: zod_1.z.string().default("9-18"),
    deadline: zod_1.z.string().nullable().optional(),
});
exports.scheduleRequestSchema = zod_1.z.object({
    tasks: zod_1.z.array(exports.taskSchema).min(1),
    work_hours: zod_1.z.string().default("9-18"),
    date: zod_1.z.string().nullable().optional(),
});
exports.rescheduleRequestSchema = zod_1.z.object({
    remaining_tasks: zod_1.z.array(exports.remainingTaskSchema).min(1),
    current_time: zod_1.z.string(),
    work_hours: zod_1.z.string().default("9-18"),
    state_signal: zod_1.z.record(zod_1.z.any()).nullable().optional(),
});
function normalizeWorkHours(workHours) {
    parseWorkHours(workHours);
    return workHours;
}
function normalizeCurrentTime(currentTime) {
    parseClockTime(currentTime, "current_time");
    return currentTime;
}
