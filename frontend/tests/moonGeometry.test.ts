import assert from "node:assert/strict";
import test from "node:test";
import { Vector3 } from "three";
import { createTileGeometry, cubeDirection } from "../src/views/home/viewer/moonGeometry.ts";

const radius = 1737400;
const size = 5;

test("cube faces point toward the six lunar axes", () => {
  const expected = [
    [1, 0, 0],
    [-1, 0, 0],
    [0, 1, 0],
    [0, -1, 0],
    [0, 0, 1],
    [0, 0, -1],
  ];

  for (let face = 0; face < 6; face++) {
    const direction = cubeDirection(face, 0, 0);

    assert(direction.distanceTo(new Vector3(...expected[face])) < 1e-10);
  }
});

test("height values change distance from the center in meters", () => {
  const heights = new Float32Array(size * size).fill(1000);
  const geometry = createTileGeometry({ face: 0, level: 0, x: 0, y: 0 }, heights, size, radius);
  const positions = geometry.getAttribute("position");

  for (let index = 0; index < size * size; index++) {
    const position = new Vector3().fromBufferAttribute(positions, index);

    assert(Math.abs(position.length() - (1 + 1000 / radius)) < 1e-6);
  }

  geometry.dispose();
});

test("neighboring tiles have identical shared edges", () => {
  const heights = new Float32Array(size * size).fill(-500);
  const left = createTileGeometry({ face: 0, level: 1, x: 0, y: 0 }, heights, size, radius);
  const right = createTileGeometry({ face: 0, level: 1, x: 1, y: 0 }, heights, size, radius);

  for (let row = 0; row < size; row++) {
    const a = new Vector3().fromBufferAttribute(left.getAttribute("position"), row * size + size - 1);
    const b = new Vector3().fromBufferAttribute(right.getAttribute("position"), row * size);

    assert(a.distanceTo(b) < 1e-7);
  }

  left.dispose();
  right.dispose();
});

test("surface triangles face outwards on every face", () => {
  const heights = new Float32Array(size * size);

  for (let face = 0; face < 6; face++) {
    const geometry = createTileGeometry({ face, level: 0, x: 0, y: 0 }, heights, size, radius);
    const positions = geometry.getAttribute("position");
    const indices = geometry.getIndex();
    const surfaceIndices = (size - 1) * (size - 1) * 6;

    assert(indices);

    for (let index = 0; index < surfaceIndices; index += 3) {
      const a = new Vector3().fromBufferAttribute(positions, indices.getX(index));
      const b = new Vector3().fromBufferAttribute(positions, indices.getX(index + 1));
      const c = new Vector3().fromBufferAttribute(positions, indices.getX(index + 2));
      const normal = b.clone().sub(a).cross(c.clone().sub(a));

      assert(normal.dot(a) > 0);
    }

    geometry.dispose();
  }
});

test("missing or malformed heights cannot create a terrain mesh", () => {
  const tile = { face: 0, level: 0, x: 0, y: 0 };

  assert.throws(() => createTileGeometry(tile, new Float32Array(2), size, radius), /unexpected size/);

  const heights = new Float32Array(size * size);
  heights[3] = NaN;

  assert.throws(() => createTileGeometry(tile, heights, size, radius), /missing heights/);
});

test("tile edges retain surface shading above the skirts", () => {
  const tileSize = 65;
  const heights = new Float32Array(tileSize * tileSize);
  const geometry = createTileGeometry({ face: 0, level: 2, x: 1, y: 1 }, heights, tileSize, radius);
  const positions = geometry.getAttribute("position");
  const normals = geometry.getAttribute("normal");

  for (let index = 0; index < tileSize * tileSize; index++) {
    const direction = new Vector3().fromBufferAttribute(positions, index).normalize();
    const normal = new Vector3().fromBufferAttribute(normals, index);

    assert(normal.dot(direction) > 0.9999);
  }

  geometry.dispose();
});
