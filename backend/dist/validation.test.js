"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const strict_1 = __importDefault(require("node:assert/strict"));
const validation_1 = require("./validation");
function runTest(name, fn) {
    try {
        fn();
        console.log(`PASS ${name}`);
    }
    catch (error) {
        console.error(`FAIL ${name}`);
        throw error;
    }
}
runTest("parseWorkHours converts hour ranges into minutes", () => {
    strict_1.default.deepEqual((0, validation_1.parseWorkHours)("9-18"), [540, 1080]);
});
runTest("validateTimeBlocks rejects overlapping blocks", () => {
    strict_1.default.throws(() => (0, validation_1.validateTimeBlocks)([
        { task_title: "Deep work", start: "09:00", end: "10:00", mode: "deep" },
        { task_title: "Admin", start: "09:45", end: "10:30", mode: "admin" },
    ], "9-18"), /overlaps a previous block/);
});
runTest("validateTimeBlocks rejects blocks before current_time when rescheduling", () => {
    strict_1.default.throws(() => (0, validation_1.validateTimeBlocks)([{ task_title: "Resume task", start: "13:00", end: "13:30", mode: "light" }], "9-18", "13:15"), /starts before current_time/);
});
