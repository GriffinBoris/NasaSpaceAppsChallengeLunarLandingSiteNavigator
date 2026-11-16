import type { IlluminationPatchInterface } from "../src/types/terrain/IlluminationPatchInterface.ts";
import assert from "node:assert/strict";
import test from "node:test";
import { readIlluminationStream } from "../src/utils/illuminationStream.ts";
import { ApiStreamError, getFirstApiErrorMessage } from "../src/utils/errorHandling.ts";
import type { IlluminationProgressInterface } from "../src/types/terrain/IlluminationProgressInterface.ts";

function eventStream(text: string) {
  const bytes = new TextEncoder().encode(text);
  let offset = 0;
  let cancelled = false;
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (offset === bytes.length) {
        controller.close();
        return;
      }

      controller.enqueue(bytes.slice(offset, offset + 1));
      offset++;
    },
    cancel() {
      cancelled = true;
    },
  });

  return { stream, wasCancelled: () => cancelled };
}

test("progress arrives before a result across arbitrary byte and unicode boundaries", async () => {
  const text =
    [
      { type: "progress", progress: { completed: 1, total: 2, percentage: 50, stage: "Tracing sunlight…" } },
      { type: "result", result: { radius_meters: 1250, grid_size: 3, points: [null, { visible_sun_fraction: 1, sampling_converged: true }] } },
    ]
      .map((event) => JSON.stringify(event))
      .join("\n") + "\n";
  const source = eventStream(text);
  const updates: IlluminationProgressInterface[] = [];
  const result = await readIlluminationStream<IlluminationPatchInterface>(source.stream, (progress) => updates.push(progress));

  assert.deepEqual(updates, [{ completed: 1, total: 2, percentage: 50, stage: "Tracing sunlight…" }]);
  assert.equal(result.radiusMeters, 1250);
  assert.deepEqual(result.points, [null, { visibleSunFraction: 1, samplingConverged: true }]);
  assert.equal(source.wasCancelled(), true);
  assert.equal(source.stream.locked, false);
});

test("a streamed server failure uses the shared error message and closes the reader", async () => {
  const source = eventStream('{"type":"error","message":"Terrain is incomplete."}\n');

  await assert.rejects(
    readIlluminationStream<IlluminationPatchInterface>(source.stream, () => {}),
    (error) => {
      assert.equal(getFirstApiErrorMessage(error, "Fallback"), "Terrain is incomplete.");
      return error instanceof ApiStreamError;
    }
  );

  assert.equal(source.wasCancelled(), true);
  assert.equal(source.stream.locked, false);
});

test("an interrupted response without a result fails instead of appearing complete", async () => {
  const source = eventStream('{"type":"progress","progress":{"percentage":50}}\n');

  await assert.rejects(
    readIlluminationStream<IlluminationPatchInterface>(source.stream, () => {}),
    /ended before returning a result/
  );
  assert.equal(source.stream.locked, false);
});

test("a transport abort releases the reader and allows a fresh request", async () => {
  const request = new AbortController();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      request.signal.addEventListener("abort", () => controller.error(request.signal.reason));
    },
  });
  const result = readIlluminationStream<IlluminationPatchInterface>(stream, () => {});

  request.abort();

  await assert.rejects(result, { name: "AbortError" });
  assert.equal(stream.locked, false);

  const retry = eventStream('{"type":"result","result":{"radius_meters":5000}}');

  assert.equal((await readIlluminationStream<IlluminationPatchInterface>(retry.stream, () => {})).radiusMeters, 5000);
});
