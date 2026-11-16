import assert from "node:assert/strict";
import { register } from "node:module";
import test from "node:test";
import { effectScope } from "vue";
import type { LunarFeatureInterface, LunarFeatureSearchResponseInterface } from "../src/types/terrain/LunarFeatureInterface.ts";

register(new URL("./support/aliases.mjs", import.meta.url), import.meta.url);

const { useFeatureSearch } = await import("../src/views/home/sites/useFeatureSearch.ts");
const { api } = await import("../src/utils/api.ts");

const feature: LunarFeatureInterface = {
  id: 1,
  usgsId: 948,
  name: "Bürg",
  englishName: null,
  featureType: "Crater, craters",
  latitude: 45.0734,
  longitude: 28.2081,
  diameterKm: 41,
  sourceUrl: "https://planetarynames.wr.usgs.gov/Feature/948",
};

test("search returns catalog features and distinguishes an unloaded catalog", async (context) => {
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  context.mock.method(api.features, "search", async () => ({ features: [], catalogLoaded: false }));
  await search.search();
  assert.equal(search.catalogLoaded.value, false);
  context.mock.method(api.features, "search", async () => ({ features: [feature], catalogLoaded: true }));
  search.query.value = "Burg";
  await search.search();
  assert.deepEqual(search.features.value, [feature]);
  assert.equal(search.hasSearched.value, true);
  assert.equal(search.isLoading.value, false);
  scope.stop();
});

test("changing the query discards late responses and closing cancels pending work", async (context) => {
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  const response = Promise.withResolvers<LunarFeatureSearchResponseInterface>();
  const queries: string[] = [];
  let requestSignal: AbortSignal;
  context.mock.method(api.features, "search", async (query: string, signal: AbortSignal) => {
    queries.push(query);
    requestSignal = signal;
    return response.promise;
  });
  search.query.value = "Burg";
  const pending = search.search();
  search.query.value = "Tycho";
  response.resolve({ features: [feature], catalogLoaded: true });
  await pending;
  assert.equal(requestSignal!.aborted, true);
  assert.deepEqual(search.features.value, []);
  assert.equal(search.isLoading.value, true);
  const next = search.search();
  scope.stop();
  await next;
  assert.equal(requestSignal!.aborted, true);
  assert.deepEqual(search.features.value, []);
  assert.deepEqual(queries, ["Burg", "Tycho"]);
});

test("failed searches stay visible and a subsequent search can succeed", async (context) => {
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  context.mock.method(api.features, "search", async () => {
    throw new Error("Network unavailable");
  });
  await search.search();
  assert.equal(search.errorMessage.value, "Unable to search lunar features.");
  context.mock.method(api.features, "search", async () => ({ features: [], catalogLoaded: true }));
  search.query.value = "Tycho";
  await search.search();
  assert.equal(search.errorMessage.value, "");
  assert.equal(search.hasSearched.value, true);
  scope.stop();
});

test("typing searches after a pause and short queries clear the results", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  const queries: string[] = [];
  context.mock.method(api.features, "search", async (query: string) => {
    queries.push(query);
    return { features: [feature], catalogLoaded: true };
  });

  search.query.value = "B";
  context.mock.timers.tick(1000);
  assert.deepEqual(queries, []);

  search.query.value = "Bu";
  context.mock.timers.tick(200);
  search.query.value = " Burg ";
  context.mock.timers.tick(249);
  assert.deepEqual(queries, []);
  assert.equal(search.isLoading.value, true);

  context.mock.timers.tick(1);
  await Promise.resolve();
  assert.deepEqual(queries, ["Burg"]);
  assert.deepEqual(search.features.value, [feature]);
  assert.equal(search.isLoading.value, false);

  search.query.value = " ";
  context.mock.timers.tick(1000);
  assert.deepEqual(queries, ["Burg"]);
  assert.deepEqual(search.features.value, []);
  assert.equal(search.hasSearched.value, false);
  assert.equal(search.isLoading.value, false);
  scope.stop();
});

test("submitting searches immediately without a duplicate delayed request", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  const queries: string[] = [];
  context.mock.method(api.features, "search", async (query: string) => {
    queries.push(query);
    return { features: [feature], catalogLoaded: true };
  });

  search.query.value = "Burg";
  await search.search();
  context.mock.timers.tick(1000);
  assert.deepEqual(queries, ["Burg"]);
  assert.deepEqual(search.features.value, [feature]);
  scope.stop();
});

test("closing or disposing search cancels scheduled requests", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const scope = effectScope();
  const search = scope.run(useFeatureSearch)!;
  const requests = context.mock.method(api.features, "search");

  search.query.value = "Burg";
  search.clear();
  context.mock.timers.tick(1000);
  assert.equal(requests.mock.callCount(), 0);
  assert.equal(search.isLoading.value, false);

  search.query.value = "Tycho";
  scope.stop();
  context.mock.timers.tick(1000);
  assert.equal(requests.mock.callCount(), 0);
  assert.equal(search.isLoading.value, false);
});
