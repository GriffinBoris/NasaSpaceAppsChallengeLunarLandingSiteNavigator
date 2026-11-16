import assert from "node:assert/strict";
import { register } from "node:module";
import test from "node:test";

register(new URL("./support/aliases.mjs", import.meta.url), import.meta.url);

const { moonViewQuery, parseMoonViewQuery } = await import("../src/views/home/moonViewQuery.ts");

test("a shared link restores the point and UTC time", () => {
  assert.deepEqual(parseMoonViewQuery({ lat: "-89.45", lon: "222", r: "5", t: "2026-11-14T06:00Z" }), {
    siteId: null,
    point: null,
    time: "2026-11-14T06:00:00.000Z",
  });
  assert.deepEqual(parseMoonViewQuery({ lat: "-89.45", lon: "-12.5", r: "5" }).point, {
    location: { latitude: -89.45, longitude: -12.5 },
    radiusKm: 5,
  });
});

test("malformed or out-of-range values are ignored", () => {
  assert.deepEqual(parseMoonViewQuery({ site: "0", lat: "north", lon: "3", t: "soon" }), {
    siteId: null,
    point: null,
    time: null,
  });
  assert.equal(parseMoonViewQuery({ lat: "10", lon: "10", r: "51" }).point, null);
});

test("the query names a site instead of its coordinates and omits empty values", () => {
  const point = { location: { latitude: -89.123456, longitude: 0 }, radiusKm: 0 };

  assert.deepEqual(moonViewQuery({ siteId: 4, point, time: null }), { site: "4" });
  assert.deepEqual(moonViewQuery({ siteId: null, point, time: "2026-11-14T06:00:00.000Z" }), {
    lat: "-89.1235",
    lon: "0.0000",
    t: "2026-11-14T06:00Z",
  });
});
