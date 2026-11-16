import assert from "node:assert/strict";
import test from "node:test";
import { matchingLength, parseUtcInput, PLAN_LENGTHS, suggestPlanName, timesPerSite, toUtcInput } from "../src/views/home/plan/newPlanForm.ts";

const HOUR = 3600000;
const START = Date.parse("2026-11-12T17:00:00Z");

test("UTC inputs round-trip a timestamp as a date and a 24-hour time", () => {
  const input = toUtcInput(Date.parse("2026-11-12T07:05:00Z"));

  assert.deepEqual(input, { date: "2026-11-12", clock: "07:05" });
  assert.equal(parseUtcInput(input), Date.parse("2026-11-12T07:05:00Z"));
});

test("UTC inputs reject missing dates and times that are not 24-hour HH:MM", () => {
  assert.equal(parseUtcInput({ date: "", clock: "17:00" }), null);
  assert.equal(parseUtcInput({ date: "2026-11-12", clock: "5:00" }), null);
  assert.equal(parseUtcInput({ date: "2026-11-12", clock: "24:00" }), null);
  assert.equal(parseUtcInput({ date: "2026-11-12", clock: "5pm" }), null);
});

test("a preset length stays active after its end is rounded to whole minutes", () => {
  const lunarDay = PLAN_LENGTHS[2]!;
  const end = parseUtcInput(toUtcInput(START + lunarDay.hours * HOUR))!;

  assert.equal(matchingLength(end - START), lunarDay);
  assert.equal(matchingLength(14 * 24 * HOUR), PLAN_LENGTHS[1]);
  assert.equal(matchingLength(3 * 24 * HOUR), null);
});

test("each site is checked once per step, counting a partial final step", () => {
  assert.equal(timesPerSite(24 * HOUR, 3600), 24);
  assert.equal(timesPerSite(90 * 60000, 3600), 2);
  assert.equal(timesPerSite(0, 3600), 0);
  assert.equal(timesPerSite(-HOUR, 3600), 0);
});

test("the suggested name describes the sites and the UTC days the plan covers", () => {
  assert.equal(suggestPlanName(["Shackleton rim"], START, START + 14 * 24 * HOUR), "Shackleton rim, Nov 12 to Nov 26");
  assert.equal(suggestPlanName(["Shackleton rim", "Polar reference point"], START, START + 24 * HOUR), "2 sites, Nov 12 to Nov 13");
  assert.equal(suggestPlanName(["Shackleton rim"], START, START + 3 * HOUR), "Shackleton rim, Nov 12");
  assert.equal(suggestPlanName([], START, START + HOUR), "");
});
