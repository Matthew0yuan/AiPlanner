import assert from "node:assert/strict";

import { parseWorkHours, validateTimeBlocks } from "./validation";

function runTest(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

runTest("parseWorkHours converts hour ranges into minutes", () => {
  assert.deepEqual(parseWorkHours("9-18"), [540, 1080]);
});

runTest("validateTimeBlocks rejects overlapping blocks", () => {
  assert.throws(
    () =>
      validateTimeBlocks(
        [
          { task_title: "Deep work", start: "09:00", end: "10:00", mode: "deep" },
          { task_title: "Admin", start: "09:45", end: "10:30", mode: "admin" },
        ],
        "9-18",
      ),
    /overlaps a previous block/,
  );
});

runTest("validateTimeBlocks rejects blocks before current_time when rescheduling", () => {
  assert.throws(
    () =>
      validateTimeBlocks(
        [{ task_title: "Resume task", start: "13:00", end: "13:30", mode: "light" }],
        "9-18",
        "13:15",
      ),
    /starts before current_time/,
  );
});
