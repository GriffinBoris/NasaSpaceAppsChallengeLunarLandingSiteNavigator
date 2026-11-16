import assert from "node:assert/strict";
import { register } from "node:module";
import test from "node:test";
import { createPinia, setActivePinia } from "pinia";
import type { SunlightStudyInterface } from "../src/types/terrain/SunlightStudyInterface.ts";
import type { SunlightSelectionInterface, SunlightSelectionListInterface } from "../src/types/terrain/SunlightSelectionInterface.ts";

register(new URL("./support/aliases.mjs", import.meta.url), import.meta.url);

const { useSunlightStore } = await import("../src/views/home/sunlightStore.ts");
const { api } = await import("../src/utils/api.ts");

function study(id: number, status: SunlightStudyInterface["status"] = "queued"): SunlightStudyInterface {
  return {
    id,
    name: `Plan ${id}`,
    datasetId: 1,
    selections: [{ id: 1, name: "Rim", latitude: -89.9, longitude: 180, radiusMeters: null }],
    startTime: "2026-11-11T00:00:00Z",
    endTime: "2026-11-11T00:30:00Z",
    stepSeconds: 900,
    workerCount: 4,
    expectedFrames: 2,
    completedFrames: 0,
    savedResults: 0,
    resultRevision: 0,
    status,
    progress: { completed: 0, total: 2, percentage: 0, stage: "Queued" },
    errorMessage: "",
    createdTs: "2026-11-11T00:00:00Z",
  };
}

const parameters = {
  name: "Plan",
  datasetId: 1,
  selectionIds: [1],
  startTime: "2026-11-11T00:00:00Z",
  endTime: "2026-11-11T00:30:00Z",
  stepSeconds: 900,
  workerCount: 4,
};

const selection: SunlightSelectionInterface = {
  id: 1,
  name: "Rim",
  latitude: -89.9,
  longitude: 180,
  radiusMeters: null,
  createdTs: "2026-11-11T00:00:00Z",
  updatedTs: "2026-11-11T00:00:00Z",
};

test("an older initial load cannot erase a newly saved site", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const response = Promise.withResolvers<SunlightSelectionListInterface>();

  context.mock.method(api.selections, "list", () => response.promise);
  context.mock.method(api.studies, "list", async () => []);
  context.mock.method(api.selections, "create", async () => selection);

  const loading = store.loadLists();

  await store.saveSelection(selection);
  response.resolve({ selections: [], stepOptions: [], workerOptions: [], defaultWorkerCount: 4 });
  await loading;

  assert.deepEqual(store.selections, [selection]);
  store.$dispose();
});

test("deleting a plan reports failure even when it is absent from the list", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();

  context.mock.method(api.studies, "remove", async () => {
    throw new Error("Network Error");
  });

  assert.equal(await store.removeStudy(1), false);
  assert.equal(store.errorMessage, "Unable to delete this plan.");

  context.mock.method(api.studies, "remove", async () => {});

  assert.equal(await store.removeStudy(1), true);
  assert.equal(store.errorMessage, "");
  store.$dispose();
});

test("refreshing lists while saving a site still accepts the saved response", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const response = Promise.withResolvers<SunlightSelectionInterface>();

  context.mock.method(api.selections, "create", () => response.promise);
  context.mock.method(api.selections, "list", async () => ({ selections: [], stepOptions: [], workerOptions: [], defaultWorkerCount: 4 }));
  context.mock.method(api.studies, "list", async () => []);

  const saving = store.saveSelection(selection);

  await store.loadLists();
  response.resolve(selection);

  assert.deepEqual(await saving, selection);
  assert.deepEqual(store.selections, [selection]);
  store.$dispose();
});

for (const action of ["save", "rename", "removeSite", "removePlan"] as const) {
  for (const outcome of ["success", "failure"] as const) {
    test(`leaving the view ignores late ${action} ${outcome}`, async (context) => {
      setActivePinia(createPinia());

      const store = useSunlightStore();
      const response = Promise.withResolvers<SunlightSelectionInterface>();

      store.selections = [selection];
      store.studies = [study(1)];
      store.focusSelection(selection.id);

      context.mock.method(api.selections, "create", () => response.promise);
      context.mock.method(api.selections, "rename", () => response.promise);
      context.mock.method(api.selections, "remove", async () => {
        await response.promise;
      });
      context.mock.method(api.studies, "remove", async () => {
        await response.promise;
      });

      const actions = {
        save: () => store.saveSelection(selection),
        rename: () => store.renameSelection(selection.id, "Renamed rim"),
        removeSite: () => store.removeSelection(selection.id),
        removePlan: () => store.removeStudy(1),
      };
      const pending = actions[action]();

      store.dispose();
      store.errorMessage = "Current view error";

      if (outcome === "success") {
        response.resolve({ ...selection, name: "Renamed rim" });
      } else {
        response.reject(new Error("Request failed"));
      }

      await pending;

      assert.deepEqual(store.selections, [selection]);
      assert.equal(store.focusedSelectionId, selection.id);
      assert.deepEqual(
        store.studies.map((plan) => plan.id),
        [1]
      );
      assert.equal(store.errorMessage, "Current view error");
      store.$dispose();
    });
  }
}

test("an old calculation response cannot clear a pending action in the reopened view", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const oldResponse = Promise.withResolvers<SunlightStudyInterface>();
  const newResponse = Promise.withResolvers<SunlightStudyInterface>();

  store.studies = [study(1, "stopped")];
  context.mock.method(api.studies, "calculate", () => oldResponse.promise);

  const oldAction = store.calculateStudy(1);

  store.dispose();
  context.mock.method(api.studies, "calculate", () => newResponse.promise);

  const newAction = store.calculateStudy(1);

  oldResponse.resolve(study(1));
  await oldAction;

  assert.equal(store.pendingStudyIds.has(1), true);

  newResponse.resolve(study(1));
  await newAction;

  assert.equal(store.pendingStudyIds.size, 0);
  assert.equal(store.studies[0]!.status, "queued");
  store.$dispose();
});

test("leaving during a queue-error refresh does not overwrite the current view error", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const refreshStarted = Promise.withResolvers<void>();
  const response = Promise.withResolvers<SunlightStudyInterface[]>();

  context.mock.method(api.studies, "calculate", async () => {
    throw new Error("Redis is unavailable");
  });
  context.mock.method(api.studies, "list", () => {
    refreshStarted.resolve();
    return response.promise;
  });

  const calculation = store.calculateStudy(1);

  await refreshStarted.promise;
  store.dispose();
  store.errorMessage = "Current view error";
  response.resolve([study(1, "failed")]);
  await calculation;

  assert.equal(store.errorMessage, "Current view error");
  assert.equal(store.studies.length, 0);
  store.$dispose();
});

test("creating multiple plans queues each without a singleton calculation request", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  let nextId = 1;
  const startRequest = context.mock.method(api.studies, "calculate");

  context.mock.method(api.studies, "create", async () => study(nextId++));

  const created = await Promise.all([store.createStudy(parameters), store.createStudy(parameters)]);

  assert.deepEqual(created.map((plan) => plan!.id).sort(), [1, 2]);
  assert.deepEqual(store.studies.map((plan) => plan.id).sort(), [1, 2]);
  assert.equal(store.hasProcessingStudies, true);
  assert.equal(startRequest.mock.callCount(), 0);
  store.$dispose();
});

test("continuing a plan sends the selected worker count and keeps the returned setting", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const stopped = study(1, "stopped");

  store.studies = [stopped];

  const calculation = context.mock.method(api.studies, "calculate", async () => ({ ...stopped, status: "queued" as const, workerCount: 16 }));

  await store.calculateStudy(1, 16);

  assert.deepEqual(calculation.mock.calls[0]!.arguments, [1, 16]);
  assert.equal(store.studies[0]!.workerCount, 16);
  assert.equal(store.studies[0]!.status, "queued");
  store.$dispose();
});

test("polling updates terrain preparation while the plan still has no results", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const running = study(1, "running");
  const updated: SunlightStudyInterface = {
    ...running,
    progress: { completed: 2, total: 5, percentage: 40, stage: "Preparing terrain, 2 of 5", phase: "preparing" },
  };

  store.studies = [running];
  context.mock.method(api.studies, "list", async () => [updated]);
  const detailRequest = context.mock.method(api.studies, "detail");

  await store.refreshStudies(new AbortController().signal);

  assert.equal(store.studies[0]!.progress!.percentage, 40);
  assert.equal(store.studies[0]!.progress!.stage, "Preparing terrain, 2 of 5");
  assert.equal(store.studies[0]!.progress!.phase, "preparing");
  assert.equal(store.studies[0]!.completedFrames, 0);
  assert.equal(detailRequest.mock.callCount(), 0);
  store.$dispose();
});

test("an older poll cannot erase a newly created plan", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const first = study(1, "running");
  const response = Promise.withResolvers<SunlightStudyInterface[]>();

  store.studies = [first];
  context.mock.method(api.studies, "list", () => response.promise);
  context.mock.method(api.studies, "create", async () => study(2));

  const refreshing = store.refreshStudies(new AbortController().signal);

  await store.createStudy(parameters);
  response.resolve([first]);
  await refreshing;

  assert.deepEqual(store.studies.map((plan) => plan.id).sort(), [1, 2]);
  store.$dispose();
});

test("stopping one plan leaves other jobs available and queued", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();

  store.studies = [study(1, "running"), study(2, "stopped")];
  context.mock.method(api.studies, "stop", async () => study(1, "stopping"));
  context.mock.method(api.studies, "calculate", async () => study(2));

  await Promise.all([store.stopStudy(1), store.calculateStudy(2)]);

  assert.equal(store.studies.find((plan) => plan.id === 1)!.status, "stopping");
  assert.equal(store.studies.find((plan) => plan.id === 2)!.status, "queued");
  assert.equal(store.pendingStudyIds.size, 0);
  store.$dispose();
});

test("leaving the view ignores late progress without stopping server jobs", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const response = Promise.withResolvers<SunlightStudyInterface[]>();
  const stop = context.mock.method(api.studies, "stop");

  store.studies = [study(1, "running")];
  context.mock.method(api.studies, "list", () => response.promise);

  const refreshing = store.refreshStudies(new AbortController().signal);

  store.dispose();
  response.resolve([study(1, "complete")]);
  await refreshing;

  assert.equal(store.studies[0]!.status, "running");
  assert.equal(stop.mock.callCount(), 0);
  store.$dispose();
});

test("a queue failure refreshes its saved error and allows another attempt", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const failed = { ...study(1, "failed"), errorMessage: "Redis is unavailable." };

  store.studies = [study(1, "stopped")];
  context.mock.method(api.studies, "list", async () => [failed]);
  context.mock.method(api.studies, "calculate", async () => {
    throw new Error("Connection failed");
  });

  await store.calculateStudy(1);

  assert.equal(store.studies[0]!.errorMessage, "Redis is unavailable.");
  assert.equal(store.pendingStudyIds.size, 0);
  assert.ok(store.errorMessage);

  context.mock.method(api.studies, "calculate", async () => study(1));

  await store.calculateStudy(1);

  assert.equal(store.studies[0]!.status, "queued");
  assert.equal(store.errorMessage, "");
  store.$dispose();
});

test("reopening the view reloads active jobs without starting them again", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const start = context.mock.method(api.studies, "calculate");

  context.mock.method(api.selections, "list", async () => ({ selections: [], stepOptions: [], workerOptions: [], defaultWorkerCount: 4 }));
  context.mock.method(api.studies, "list", async () => [study(1, "running"), study(2)]);

  await store.loadLists();

  assert.equal(store.studies.length, 2);
  assert.equal(store.hasProcessingStudies, true);
  assert.equal(start.mock.callCount(), 0);
  store.$dispose();
});

test("a successful refresh clears an earlier refresh failure but keeps other errors", async (context) => {
  setActivePinia(createPinia());

  const store = useSunlightStore();
  const running = study(1, "running");
  let shouldFail = true;

  store.studies = [running];
  context.mock.method(api.studies, "list", async () => {
    if (shouldFail) throw new Error("Network Error");

    return [running];
  });

  await store.refreshStudies(new AbortController().signal);
  assert.equal(store.errorMessage, "Unable to refresh plan progress. Trying again.");

  shouldFail = false;
  await store.refreshStudies(new AbortController().signal);
  assert.equal(store.errorMessage, "");

  store.errorMessage = "Unable to delete this plan.";
  await store.refreshStudies(new AbortController().signal);
  assert.equal(store.errorMessage, "Unable to delete this plan.");
  store.$dispose();
});
