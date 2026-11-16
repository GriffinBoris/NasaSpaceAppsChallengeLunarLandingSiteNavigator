import { BufferGeometry, Float32BufferAttribute, Vector3 } from "three";
import type { TerrainTileInterface } from "@/types/terrain/TerrainTileInterface";
import { elevationColor } from "./elevationColors.ts";

export function cubeDirection(face: number, horizontal: number, vertical: number): Vector3 {
  let direction: Vector3;

  switch (face) {
    case 0:
      direction = new Vector3(1, vertical, -horizontal);
      break;
    case 1:
      direction = new Vector3(-1, vertical, horizontal);
      break;
    case 2:
      direction = new Vector3(horizontal, 1, -vertical);
      break;
    case 3:
      direction = new Vector3(horizontal, -1, vertical);
      break;
    case 4:
      direction = new Vector3(horizontal, vertical, 1);
      break;
    case 5:
      direction = new Vector3(-horizontal, vertical, -1);
      break;
    default:
      throw new Error("Unknown terrain face.");
  }

  return direction.normalize();
}

export function tileCenter(tile: TerrainTileInterface): Vector3 {
  const tilesPerAxis = 2 ** tile.level;
  const horizontal = -1 + (2 * (tile.x + 0.5)) / tilesPerAxis;
  const vertical = 1 - (2 * (tile.y + 0.5)) / tilesPerAxis;

  return cubeDirection(tile.face, horizontal, vertical);
}

export function createTileGeometry(tile: TerrainTileInterface, heights: Float32Array, tileSize: number, referenceRadius: number): BufferGeometry {
  if (heights.length !== tileSize * tileSize) {
    throw new Error("The terrain tile has an unexpected size.");
  }

  const positions: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];

  const tilesPerAxis = 2 ** tile.level;
  const segmentCount = tileSize - 1;

  for (let row = 0; row < tileSize; row++) {
    const vertical = 1 - (2 * (tile.y + row / segmentCount)) / tilesPerAxis;

    for (let column = 0; column < tileSize; column++) {
      const horizontal = -1 + (2 * (tile.x + column / segmentCount)) / tilesPerAxis;
      const direction = cubeDirection(tile.face, horizontal, vertical);
      const height = heights[row * tileSize + column]!;

      if (!Number.isFinite(height)) {
        throw new Error("The terrain tile contains missing heights.");
      }

      const radius = 1 + height / referenceRadius;
      const color = elevationColor(height);

      positions.push(direction.x * radius, direction.y * radius, direction.z * radius);
      colors.push(color.r, color.g, color.b);
    }
  }

  for (let row = 0; row < segmentCount; row++) {
    for (let column = 0; column < segmentCount; column++) {
      const topLeft = row * tileSize + column;
      const topRight = topLeft + 1;
      const bottomLeft = topLeft + tileSize;
      const bottomRight = bottomLeft + 1;

      indices.push(topLeft, bottomLeft, topRight);
      indices.push(topRight, bottomLeft, bottomRight);
    }
  }

  const geometry = new BufferGeometry();

  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  const normals = Array.from(geometry.getAttribute("normal").array);
  const edgeVertices: number[] = [];

  for (let column = 0; column < tileSize; column++) {
    edgeVertices.push(column);
  }

  for (let row = 1; row < tileSize; row++) {
    edgeVertices.push(row * tileSize + segmentCount);
  }

  for (let column = segmentCount - 1; column >= 0; column--) {
    edgeVertices.push(segmentCount * tileSize + column);
  }

  for (let row = segmentCount - 1; row > 0; row--) {
    edgeVertices.push(row * tileSize);
  }

  const skirtDepth = Math.max(2500, 20000 / tilesPerAxis) / referenceRadius;
  const skirtStart = positions.length / 3;

  for (const vertexIndex of edgeVertices) {
    const position = new Vector3(positions[vertexIndex * 3], positions[vertexIndex * 3 + 1], positions[vertexIndex * 3 + 2]);
    const radius = position.length();

    position.multiplyScalar((radius - skirtDepth) / radius);
    positions.push(position.x, position.y, position.z);
    colors.push(colors[vertexIndex * 3]!, colors[vertexIndex * 3 + 1]!, colors[vertexIndex * 3 + 2]!);
    normals.push(normals[vertexIndex * 3]!, normals[vertexIndex * 3 + 1]!, normals[vertexIndex * 3 + 2]!);
  }

  for (let edgeIndex = 0; edgeIndex < edgeVertices.length; edgeIndex++) {
    const nextEdgeIndex = (edgeIndex + 1) % edgeVertices.length;

    indices.push(edgeVertices[edgeIndex]!, skirtStart + edgeIndex, edgeVertices[nextEdgeIndex]!);
    indices.push(edgeVertices[nextEdgeIndex]!, skirtStart + edgeIndex, skirtStart + nextEdgeIndex);
  }

  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new Float32BufferAttribute(colors, 3));
  geometry.setAttribute("normal", new Float32BufferAttribute(normals, 3));

  geometry.setIndex(indices);
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  return geometry;
}
