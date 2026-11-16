import assert from "node:assert/strict";
import test from "node:test";
import { nextGridCell } from "../src/composables/useGridNavigation.ts";

test("arrow keys move one cell and stop at the grid edges", () => {
  assert.deepEqual(nextGridCell({ row: 1, column: 1 }, "ArrowRight", 3, 4), { row: 1, column: 2 });
  assert.deepEqual(nextGridCell({ row: 1, column: 1 }, "ArrowUp", 3, 4), { row: 0, column: 1 });
  assert.equal(nextGridCell({ row: 0, column: 0 }, "ArrowLeft", 3, 4), null);
  assert.equal(nextGridCell({ row: 2, column: 3 }, "ArrowDown", 3, 4), null);
});

test("Home and End jump to the first and last cell in the row", () => {
  assert.deepEqual(nextGridCell({ row: 2, column: 2 }, "Home", 3, 4), { row: 2, column: 0 });
  assert.deepEqual(nextGridCell({ row: 2, column: 0 }, "End", 3, 4), { row: 2, column: 3 });
  assert.equal(nextGridCell({ row: 2, column: 0 }, "Enter", 3, 4), null);
});
