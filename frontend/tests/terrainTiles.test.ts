import assert from "node:assert/strict";
import test from "node:test";
import { PerspectiveCamera, Vector3, type BufferGeometry, type Mesh, type MeshStandardMaterial } from "three";
import type { TerrainDatasetInterface } from "../src/types/terrain/TerrainDatasetInterface.ts";
import type { TerrainDetailInterface } from "../src/types/terrain/TerrainDetailInterface.ts";
import { TerrainTiles } from "../src/views/home/viewer/terrainTiles.ts";
import { TerrainView } from "../src/views/home/viewer/terrainView.ts";

const dataset: TerrainDatasetInterface = {
  id: 1,
  name: "moon",
  storageKey: "test",
  frame: "MOON_ME_DE421",
  referenceRadius: 1737400,
  tileSize: 5,
  maxLevel: 1,
  tileCount: 10,
  refinements: ["0/0/0/0"],
  sources: [],
  tileUrlTemplate: "unused",
};

function createView(height = 600, position = new Vector3(3, 0, 0)): TerrainView {
  const camera = new PerspectiveCamera(42, 1, 0.01, 20);

  camera.position.copy(position);
  camera.lookAt(0, 0, 0);

  return new TerrainView(camera, height);
}

function createRefinedDataset(maximumLevel: number): TerrainDatasetInterface {
  const refinements: string[] = [];

  for (let face = 0; face < 6; face++) {
    for (let level = 0; level < maximumLevel; level++) {
      for (let row = 0; row < 2 ** level; row++) {
        for (let column = 0; column < 2 ** level; column++) {
          refinements.push(`${face}/${level}/${column}/${row}`);
        }
      }
    }
  }

  return {
    ...dataset,
    maxLevel: maximumLevel,
    tileCount: (6 * (4 ** (maximumLevel + 1) - 1)) / 3,
    refinements,
  };
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((complete) => {
    resolve = complete;
  });

  return { promise, resolve };
}

test("terrain loading overlaps requests without exceeding four at a time", async () => {
  const releaseLoads = deferred();
  let active = 0;
  let peak = 0;
  let requests = 0;
  const tiles = new TerrainTiles(
    dataset,
    async () => {
      active += 1;
      requests += 1;
      peak = Math.max(peak, active);

      await releaseLoads.promise;
      active -= 1;

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  try {
    const loading = tiles.initialize();

    assert.equal(active, 4);
    releaseLoads.resolve();
    await loading;
    await tiles.requestUpdate(createView());

    assert.equal(peak, 4);
    assert.equal(requests, 10);
    assert.equal(active, 0);
  } finally {
    releaseLoads.resolve();
    tiles.dispose();
  }
});

test("coarse terrain remains visible until all four children load", async () => {
  const lastChildRequested = deferred();
  const releaseLastChild = deferred();
  const details: (TerrainDetailInterface | null)[] = [];
  let childRequests = 0;
  const tiles = new TerrainTiles(
    dataset,
    async (key) => {
      if (key.level === 1) {
        childRequests += 1;

        if (childRequests === 4) {
          lastChildRequested.resolve();
          await releaseLastChild.promise;
        }
      }

      return new Float32Array(25);
    },
    (detail) => details.push(detail),
    () => {}
  );

  try {
    await tiles.initialize();

    assert.deepEqual(details.at(-1), {
      minimumLevel: 0,
      maximumLevel: 0,
      maximumAvailableLevel: 1,
      isLoading: false,
    });

    const parent = tiles.group.children[0]!;
    const updating = tiles.requestUpdate(createView());

    await lastChildRequested.promise;

    assert(parent.visible);
    assert(tiles.group.children.slice(6).every((child) => !child.visible));
    assert.equal(details.at(-1)?.maximumLevel, 0);
    assert.equal(details.at(-1)?.isLoading, true);

    releaseLastChild.resolve();
    await updating;

    assert(!parent.visible);
    assert.equal(tiles.group.children.slice(6).filter((child) => child.visible).length, 4);
    assert.equal(details.at(-1)?.maximumLevel, 1);
    assert.equal(details.at(-1)?.isLoading, false);
  } finally {
    releaseLastChild.resolve();
    tiles.dispose();
  }
});

test("failed detail keeps coarse terrain and can be retried", async () => {
  let shouldFail = true;
  const errors: boolean[] = [];
  const details: (TerrainDetailInterface | null)[] = [];
  const tiles = new TerrainTiles(
    dataset,
    async (key) => {
      if (key.level === 1 && shouldFail) {
        throw new Error("The tile request failed.");
      }

      return new Float32Array(25);
    },
    (detail) => details.push(detail),
    (hasError) => errors.push(hasError)
  );

  try {
    await tiles.initialize();
    await tiles.requestUpdate(createView());

    assert(tiles.group.children[0]!.visible);
    assert.deepEqual(errors, [true]);
    assert.equal(details.at(-1)?.maximumLevel, 0);
    assert.equal(details.at(-1)?.isLoading, false);

    shouldFail = false;
    await tiles.requestUpdate(createView());

    assert(!tiles.group.children[0]!.visible);
    assert.deepEqual(errors, [true, false]);
  } finally {
    tiles.dispose();
  }
});

test("zooming out restores cached parents without fetching tiles", async () => {
  let requests = 0;
  const details: (TerrainDetailInterface | null)[] = [];
  const tiles = new TerrainTiles(
    dataset,
    async () => {
      requests += 1;

      return new Float32Array(25);
    },
    (detail) => details.push(detail),
    () => {}
  );

  try {
    await tiles.initialize();
    await tiles.requestUpdate(createView());

    assert.equal(details.at(-1)?.maximumLevel, 1);

    const loadedRequests = requests;

    await tiles.requestUpdate(createView(1));

    assert(tiles.group.children[0]!.visible);
    assert(tiles.group.children.slice(6).every((child) => !child.visible));
    assert.equal(requests, loadedRequests);
    assert.equal(details.at(-1)?.maximumLevel, 0);

    await tiles.requestUpdate(createView());

    assert.equal(requests, loadedRequests);
    assert.equal(details.at(-1)?.maximumLevel, 1);
  } finally {
    tiles.dispose();
  }
});

test("a failed tile batch settles before retrying and keeps successful siblings cached", async () => {
  const siblingsRequested = deferred();
  const releaseSiblings = deferred();
  const errors: boolean[] = [];
  let requests = 0;
  let childRequests = 0;
  let failFirstChild = true;
  const tiles = new TerrainTiles(
    dataset,
    async (coordinates) => {
      requests += 1;

      if (coordinates.level === 1) {
        childRequests += 1;

        if (childRequests === 4) siblingsRequested.resolve();

        if (failFirstChild && coordinates.x === 0 && coordinates.y === 0) {
          failFirstChild = false;
          throw new Error("Tile failed.");
        }

        await releaseSiblings.promise;
      }

      return new Float32Array(25);
    },
    () => {},
    (hasError) => errors.push(hasError)
  );

  try {
    await tiles.initialize();

    const updating = tiles.requestUpdate(createView());

    await siblingsRequested.promise;
    assert.deepEqual(errors, []);
    assert(tiles.group.children[0]!.visible);

    releaseSiblings.resolve();
    await updating;
    assert.deepEqual(errors, [true]);

    await tiles.requestUpdate(createView());
    assert.equal(requests, 11);
    assert.deepEqual(errors, [true, false]);
    assert(!tiles.group.children[0]!.visible);
  } finally {
    releaseSiblings.resolve();
    tiles.dispose();
  }
});

test("zooming out coarsens immediately from cached parents and never adds detail", async () => {
  let requests = 0;
  const details: (TerrainDetailInterface | null)[] = [];
  const tiles = new TerrainTiles(
    dataset,
    async () => {
      requests += 1;

      return new Float32Array(25);
    },
    (detail) => details.push(detail),
    () => {}
  );

  try {
    await tiles.initialize();
    await tiles.requestUpdate(createView());

    const loadedRequests = requests;

    assert.equal(details.at(-1)?.maximumLevel, 1);

    tiles.coarsen(createView(1));

    assert(tiles.group.children[0]!.visible);
    assert(tiles.group.children.slice(6).every((child) => !child.visible));
    assert.equal(details.at(-1)?.maximumLevel, 0);

    tiles.coarsen(createView());

    assert(tiles.group.children.slice(6).every((child) => !child.visible));
    assert.equal(details.at(-1)?.maximumLevel, 0);
    assert.equal(requests, loadedRequests);
  } finally {
    tiles.dispose();
  }
});

test("detail levels exclude offscreen coarse meshes and hidden cached detail", async () => {
  const details: (TerrainDetailInterface | null)[] = [];
  const tiles = new TerrainTiles(
    { ...dataset, maxLevel: 9 },
    async () => new Float32Array(25),
    (detail) => details.push(detail),
    () => {}
  );
  const view = createView();

  view.isVisible = (_boundingSphere, center) => center.x > 0.5;

  try {
    await tiles.initialize();
    await tiles.requestUpdate(view);

    assert(tiles.group.children.slice(1, 6).every((mesh) => mesh.visible));
    assert.deepEqual(details.at(-1), {
      minimumLevel: 1,
      maximumLevel: 1,
      maximumAvailableLevel: 9,
      isLoading: false,
    });

    await tiles.requestUpdate(createView(600, new Vector3(-3, 0, 0)));

    assert.equal(details.at(-1)?.minimumLevel, 0);
    assert.equal(details.at(-1)?.maximumLevel, 0);
  } finally {
    tiles.dispose();
  }
});

test("rotating away keeps coarse terrain across the Moon and reuses detail on return", async () => {
  let requests = 0;
  const tiles = new TerrainTiles(
    dataset,
    async () => {
      requests += 1;

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  try {
    await tiles.initialize();
    await tiles.requestUpdate(createView());

    const loadedRequests = requests;

    assert(tiles.group.children.slice(1, 6).every((mesh) => mesh.visible));

    await tiles.requestUpdate(createView(600, new Vector3(-3, 0, 0)));

    assert(tiles.group.children.slice(0, 6).every((mesh) => mesh.visible));
    assert(tiles.group.children.slice(6).every((mesh) => !mesh.visible));

    await tiles.requestUpdate(createView());

    assert.equal(requests, loadedRequests);
    assert(!tiles.group.children[0]!.visible);
    assert(tiles.group.children.slice(6).every((mesh) => mesh.visible));
  } finally {
    tiles.dispose();
  }
});

test("recent detail survives a rotation around all six faces", async () => {
  let requests = 0;
  const tiles = new TerrainTiles(
    createRefinedDataset(3),
    async () => {
      requests += 1;

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  try {
    await tiles.initialize();

    for (const position of [
      new Vector3(3, 0, 0),
      new Vector3(-3, 0, 0),
      new Vector3(0, 3, 0),
      new Vector3(0, -3, 0),
      new Vector3(0, 0, 3),
      new Vector3(0, 0, -3),
    ]) {
      await tiles.requestUpdate(createView(100000, position));
    }

    const loadedRequests = requests;

    assert(loadedRequests > 128);

    await tiles.requestUpdate(createView(100000));

    assert.equal(requests, loadedRequests);
  } finally {
    tiles.dispose();
  }
});

test("cache pressure releases old geometry while keeping recently revisited detail", async () => {
  let requests = 0;
  let disposedGeometries = 0;
  const tiles = new TerrainTiles(
    createRefinedDataset(7),
    async () => {
      requests += 1;

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  const firstArea = createView(600, new Vector3(1.02, 0, 0));
  const oldestArea = createView(600, new Vector3(-1.02, 0, 0));

  try {
    await tiles.initialize();
    await tiles.requestUpdate(firstArea);
    await tiles.requestUpdate(oldestArea);
    await tiles.requestUpdate(createView(600, new Vector3(0, 1.02, 0)));

    for (const mesh of tiles.group.children as Mesh[]) {
      mesh.geometry.addEventListener("dispose", () => {
        disposedGeometries += 1;
      });
    }

    await tiles.requestUpdate(firstArea);
    await tiles.requestUpdate(createView(600, new Vector3(0, -1.02, 0)));
    await tiles.requestUpdate(createView(600, new Vector3(0, 0, 1.02)));
    await tiles.requestUpdate(createView(600, new Vector3(0, 0, -1.02)));

    const loadedRequests = requests;

    assert(loadedRequests > 512);
    assert(tiles.group.children.length <= 512);
    assert(disposedGeometries > 0);

    await tiles.requestUpdate(firstArea);

    assert.equal(requests, loadedRequests);

    await tiles.requestUpdate(oldestArea);

    assert(requests > loadedRequests);
  } finally {
    tiles.dispose();
  }
});

test("a changed view stops refinement from the previous view", async () => {
  const childRequested = deferred();
  const releaseChild = deferred();
  let childRequests = 0;
  const tiles = new TerrainTiles(
    dataset,
    async (key) => {
      if (key.level === 1) {
        childRequests += 1;
        childRequested.resolve();
        await releaseChild.promise;
      }

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  try {
    await tiles.initialize();

    const updating = tiles.requestUpdate(createView());

    await childRequested.promise;
    tiles.requestUpdate(createView(1));
    releaseChild.resolve();
    await updating;

    assert.equal(childRequests, 4);
    assert(tiles.group.children[0]!.visible);
    assert(tiles.group.children.slice(6).every((child) => !child.visible));
  } finally {
    releaseChild.resolve();
    tiles.dispose();
  }
});

test("disposal aborts loading and prevents late meshes from being attached", async () => {
  const childRequested = deferred();
  const releaseChild = deferred();
  let pendingSignal: AbortSignal;
  const tiles = new TerrainTiles(
    dataset,
    async (key, signal) => {
      if (key.level === 1) {
        pendingSignal = signal;
        childRequested.resolve();
        await releaseChild.promise;
      }

      return new Float32Array(25);
    },
    () => {},
    () => {}
  );

  await tiles.initialize();

  const updating = tiles.requestUpdate(createView());

  await childRequested.promise;
  tiles.dispose();

  assert(pendingSignal!.aborted);
  assert.equal(tiles.group.children.length, 0);

  releaseChild.resolve();
  await updating;

  assert.equal(tiles.group.children.length, 0);
});

test("disposal stops render notifications from an unfinished selection", async () => {
  let changes = 0;
  const errors: boolean[] = [];
  const tiles = new TerrainTiles(
    dataset,
    async () => new Float32Array(25),
    () => {
      changes += 1;
    },
    (hasError) => errors.push(hasError)
  );

  await tiles.initialize();
  changes = 0;

  const updating = tiles.requestUpdate(createView(1));
  const changesAtDisposal = changes;

  tiles.dispose();
  await updating;

  assert.equal(changes, changesAtDisposal);
  assert.deepEqual(errors, []);
});

test("elevation color toggles affect existing and newly loaded tiles without refetching", async () => {
  let requests = 0;
  const tiles = new TerrainTiles(
    dataset,
    async () => {
      requests += 1;

      return new Float32Array(25).fill(1000);
    },
    () => {},
    () => {}
  );

  try {
    await tiles.initialize();

    const initialRequests = requests;
    const rootMesh = tiles.group.children[0] as Mesh<BufferGeometry, MeshStandardMaterial>;

    assert.equal(rootMesh.material.vertexColors, false);

    tiles.setDisplayMode("elevation");

    assert.equal(requests, initialRequests);
    assert.equal(rootMesh.material.vertexColors, true);
    assert.equal(rootMesh.material.color.getHexString(), "ffffff");

    await tiles.requestUpdate(createView());

    for (const mesh of tiles.group.children as Mesh<BufferGeometry, MeshStandardMaterial>[]) {
      assert.equal(mesh.material.vertexColors, true);
    }

    const loadedRequests = requests;

    tiles.setDisplayMode("terrain");

    assert.equal(requests, loadedRequests);
    assert.equal(rootMesh.material.vertexColors, false);
    assert.equal(rootMesh.material.color.getHexString(), "aaaaaa");
  } finally {
    tiles.dispose();
  }
});
