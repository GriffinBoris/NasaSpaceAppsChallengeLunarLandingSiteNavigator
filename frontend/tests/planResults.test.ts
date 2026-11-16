import assert from "node:assert/strict";
import test from "node:test";
import type { SunlightFrameInterface } from "../src/types/terrain/SunlightFrameInterface.ts";
import { mergeFrames } from "../src/views/home/plan/planResults.ts";

function frame(id: number, resultRevision = 1): SunlightFrameInterface {
  return {
    id,
    resultRevision,
    studyId: 1,
    selectionId: 1,
    timestamp: `2026-11-14T0${id}:00:00Z`,
    visibleSunFraction: 1,
    visibleEarthFraction: null,
    earthCenterVisible: null,
    jointVisibleShare: null,
    thumbnail: null,
    earthThumbnail: null,
  };
}

test("changed frames replace an existing body result while retaining other times", () => {
  const first = frame(1);
  const second = frame(2);
  const paired = { ...first, resultRevision: 3, visibleEarthFraction: 1, earthCenterVisible: true, jointVisibleShare: 1 };
  const result = mergeFrames([first, second], [paired], false);

  assert.deepEqual(result, [paired, second]);
  assert.equal(result[1], second);
  assert.deepEqual(mergeFrames(result, [first], false), result);
  assert.equal(mergeFrames(result, [], false), result);
});

test("a schedule reset removes results absent from the replacement history", () => {
  const first = frame(1);
  const second = frame(2);

  assert.deepEqual(mergeFrames([first, second], [second], true), [second]);
  assert.deepEqual(mergeFrames([first], [], true), []);
});

test("new times are merged in chronological order", () => {
  assert.deepEqual(
    mergeFrames([frame(2)], [frame(3), frame(1)], false).map((result) => result.id),
    [1, 2, 3]
  );
});
