import assert from "node:assert/strict";
import test from "node:test";
import { effectScope } from "vue";
import { usePolling } from "../src/composables/usePolling.ts";

test("polling avoids overlapping requests and stops when the work completes", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });

  const scope = effectScope();
  const response = Promise.withResolvers<void>();
  let completed = false;
  let calls = 0;
  const polling = scope.run(() =>
    usePolling(
      async () => {
        calls++;
        await response.promise;
      },
      () => completed,
      2000
    )
  )!;

  polling.startPolling();
  polling.startPolling();
  context.mock.timers.tick(2000);
  context.mock.timers.tick(10000);

  assert.equal(calls, 1);

  completed = true;
  response.resolve();
  await response.promise;
  await Promise.resolve();
  context.mock.timers.tick(10000);

  assert.equal(calls, 1);
  scope.stop();
});

test("scope cleanup aborts a pending request and prevents further polling", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });

  const scope = effectScope();
  const response = Promise.withResolvers<void>();
  const requests: AbortSignal[] = [];
  const polling = scope.run(() =>
    usePolling(
      async (signal) => {
        requests.push(signal);
        await response.promise;
      },
      () => false,
      2000
    )
  )!;

  polling.startPolling();
  context.mock.timers.tick(2000);
  scope.stop();

  assert.equal(requests[0]!.aborted, true);

  response.resolve();
  await response.promise;
  await Promise.resolve();
  context.mock.timers.tick(10000);

  assert.equal(requests.length, 1);
});

test("stopping a scheduled poll prevents a request and allows a fresh start", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });

  const scope = effectScope();
  const requests: AbortSignal[] = [];
  const polling = scope.run(() =>
    usePolling(
      async (signal) => {
        requests.push(signal);
      },
      () => false,
      2000
    )
  )!;

  polling.startPolling();
  polling.stopPolling();
  context.mock.timers.tick(5000);

  assert.equal(requests.length, 0);

  polling.startPolling();
  context.mock.timers.tick(2000);
  await Promise.resolve();

  assert.equal(requests.length, 1);
  scope.stop();
});
