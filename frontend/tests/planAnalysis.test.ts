import assert from "node:assert/strict";
import test from "node:test";
import type { SunlightFrameInterface } from "../src/types/terrain/SunlightFrameInterface.ts";
import type { SunlightStudyInterface } from "../src/types/terrain/SunlightStudyInterface.ts";
import { dailySunlight, planInsight, runDuration, runDurationLabel, siteMetrics, visibilityCalendar } from "../src/views/home/plan/planAnalysis.ts";
import { planResultsCsv } from "../src/views/home/plan/planCsv.ts";
import { sunlightRuns } from "../src/views/home/plan/planTimeline.ts";

const insightText = (...args: Parameters<typeof planInsight>) => {
  const { lead, detail } = planInsight(...args);

  return [lead, detail].filter(Boolean).join(" ");
};

const HOUR = 3600000;
const start = Date.parse("2026-11-11T00:00:00Z");
const hourly = (count: number, offsetHours = 0) => Array.from({ length: count }, (_, index) => start + (index + offsetHours) * HOUR);

test("runs separate fully dark results from results with any Sun and stop at missing results", () => {
  const series = [0, 0, 0.4, 1, null, 1, 0, 0, 0];

  assert.deepEqual(sunlightRuns(series, "dark"), [
    { startIndex: 6, length: 3 },
    { startIndex: 0, length: 2 },
  ]);
  assert.deepEqual(sunlightRuns(series, "sunlit"), [
    { startIndex: 2, length: 2 },
    { startIndex: 5, length: 1 },
  ]);
});

test("site metrics count calculated results, fully lit checks, and the longest runs", () => {
  const metrics = siteMetrics([0, 0, 1, 1, 0.5, null, 0, 1]);

  assert.equal(metrics.calculatedCount, 7);
  assert.equal(metrics.average, 3.5 / 7);
  assert.equal(metrics.fullyLitShare, 3 / 7);
  assert.deepEqual(metrics.darkRuns[0], { startIndex: 0, length: 2 });
  assert.deepEqual(metrics.longestSunlit, { startIndex: 2, length: 3 });
});

test("site metrics stay empty until a result exists", () => {
  const metrics = siteMetrics([null, null]);

  assert.equal(metrics.average, null);
  assert.equal(metrics.fullyLitShare, null);
  assert.equal(metrics.longestSunlit, null);
  assert.deepEqual(metrics.darkRuns, []);
});

test("daily sunlight averages each UTC day, including partial days at the window edges", () => {
  const schedule = hourly(40, 12);
  const series = schedule.map((_, index) => (index < 12 ? 1 : index < 36 ? 0 : null));
  const days = dailySunlight(schedule, series);

  assert.deepEqual(
    days.map((day) => [new Date(day.day).toISOString().slice(0, 10), day.average, day.calculatedCount]),
    [
      ["2026-11-11", 1, 12],
      ["2026-11-12", 0, 24],
      ["2026-11-13", null, 0],
    ]
  );
});

test("the calendar averages results into hourly columns for short steps", () => {
  const schedule = Array.from({ length: 8 }, (_, index) => start + index * 15 * 60000);
  const calendar = visibilityCalendar(schedule, [1, 1, 0, 0, 0.5, null, null, null], 900)!;

  assert.equal(calendar.columnHours, 1);
  assert.equal(calendar.days.length, 1);
  assert.equal(calendar.days[0]!.cells.length, 24);
  assert.deepEqual(calendar.days[0]!.cells.slice(0, 3), [0.5, 0.5, null]);
});

test("the calendar uses wider columns for six-hour steps and is omitted for daily steps", () => {
  const schedule = Array.from({ length: 8 }, (_, index) => start + index * 6 * HOUR);
  const calendar = visibilityCalendar(schedule, [0, 1, 1, 0, 0, 0, 1, 1], 21600)!;

  assert.equal(calendar.columnHours, 6);
  assert.deepEqual(
    calendar.days.map((day) => day.cells),
    [
      [0, 1, 1, 0],
      [0, 0, 1, 1],
    ]
  );
  assert.equal(visibilityCalendar(hourly(3), [1, 1, 1], 86400), null);
});

test("the insight names the sunniest site and the site with the longest night", () => {
  const schedule = hourly(6);
  const sites = [
    { name: "Shackleton rim", metrics: siteMetrics([1, 1, 0, 1, 1, 1]) },
    { name: "Odysseus (IM-1)", metrics: siteMetrics([0, 0, 0, 0, 1, 1]) },
  ];

  assert.equal(
    insightText(sites, schedule, 3600, 6 * 3600),
    "Shackleton rim gets the most sunlight, averaging 83% visible Sun. Its longest fully dark stretch is about 1 h. " +
      "Odysseus (IM-1) has the longest night: at least 4 h, starting Nov 11, 00:00 UTC or earlier."
  );
  assert.equal(
    insightText([{ name: "Shackleton rim", metrics: siteMetrics([1, 1]) }], hourly(2), 3600, 2 * 3600),
    "Shackleton rim averages 100% visible Sun over this window. None of its samples, checked every 1 h, are fully dark."
  );
  assert.equal(insightText([{ name: "Shackleton rim", metrics: siteMetrics([null]) }], schedule, 3600, 6 * 3600), "No results yet.");
});

test("the insight does not conclude a site is never dark before every result exists", () => {
  assert.equal(
    insightText([{ name: "Shackleton rim", metrics: siteMetrics([1, null, 1]) }], hourly(3), 3600, 3 * 3600),
    "Shackleton rim averages 100% visible Sun over this window. None of its results so far are fully dark."
  );
});

test("runs touching the window edge are lower bounds and never extend past the window end", () => {
  assert.deepEqual(runDuration({ startIndex: 2, length: 1 }, 6, 3600, 6 * 3600), { text: "1 h", isBound: false });
  assert.equal(runDurationLabel({ startIndex: 2, length: 1 }, 6, 3600, 6 * 3600), "1 h");
  assert.equal(runDurationLabel({ startIndex: 0, length: 2 }, 6, 3600, 6 * 3600), "At least 2 h");
  assert.equal(runDurationLabel({ startIndex: 4, length: 2 }, 6, 3600, 5.2 * 3600), "At least 1 h");
});

test("the CSV lists results by site order and time, quotes names, and neutralizes formulas", () => {
  const study: SunlightStudyInterface = {
    id: 3,
    name: "Window",
    datasetId: 2,
    selections: [
      { id: 9, name: 'Rim, "east"', latitude: -89.9, longitude: 180, radiusMeters: 2500 },
      { id: 4, name: "Odysseus (IM-1)", latitude: -80.13, longitude: 1.44, radiusMeters: null },
      { id: 5, name: "=HYPERLINK(1)", latitude: 0, longitude: 0, radiusMeters: null },
    ],
    startTime: "2026-11-11T00:00:00Z",
    endTime: "2026-11-11T02:00:00Z",
    stepSeconds: 3600,
    workerCount: 4,
    expectedFrames: 4,
    completedFrames: 3,
    status: "stopped",
    progress: null,
    errorMessage: "",
    createdTs: "2026-11-11T00:00:00Z",
  };
  const frame = (id: number, selectionId: number, timestamp: string, visibleSunFraction: number): SunlightFrameInterface => ({
    id,
    studyId: 3,
    selectionId,
    timestamp,
    visibleSunFraction,
    thumbnail: null,
    earthThumbnail: null,
  });

  assert.equal(
    planResultsCsv(study, [
      frame(1, 4, "2026-11-11T00:00:00Z", 0),
      frame(2, 9, "2026-11-11T01:00:00Z", 1),
      frame(3, 9, "2026-11-11T00:00:00Z", 0.25),
      frame(4, 5, "2026-11-11T00:00:00Z", 1),
    ]),
    [
      "site,latitude,longitude,radius_m,timestamp_utc,visible_sun_fraction,visible_earth_fraction,earth_center_visible,joint_visible_share",
      '"Rim, ""east""",-89.9,180,2500,2026-11-11T00:00:00Z,0.25,,,',
      '"Rim, ""east""",-89.9,180,2500,2026-11-11T01:00:00Z,1,,,',
      "Odysseus (IM-1),-80.13,1.44,,2026-11-11T00:00:00Z,0,,,",
      "'=HYPERLINK(1),0,0,,2026-11-11T00:00:00Z,1,,,",
      "",
    ].join("\n")
  );
});
