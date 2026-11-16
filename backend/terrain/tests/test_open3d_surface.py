import numpy
import pytest

from terrain.services.body_geometry import disk_directions
from terrain.services.illumination import calculate_visibility
from terrain.services.open3d_surface_mesh import Open3DSurfaceBlock, Open3DSurfaceMesh
from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE, SurfaceMesh


@pytest.mark.parametrize('face', range(6))
@pytest.mark.parametrize('level', [7, 9])
def test_native_rays_match_float64_on_rough_terrain_near_the_horizon(face, level):
	random = numpy.random.default_rng(842 + face)
	heights = random.uniform(-50, 50, (33, 33))
	coordinates = (face, level, 2 ** (level - 1), 2 ** (level - 1))
	reference = SurfaceMesh(coordinates, heights, 1737400)
	candidate = Open3DSurfaceMesh(coordinates, heights, 1737400)

	assert candidate.blocks
	assert candidate.maximum_plane_error < MINIMUM_INTERSECTION_DISTANCE / 4

	for row, column in [(1, 3), (12, 19), (30, 30)]:
		triangle = reference.triangles(row, column, row + 1, column + 1)[0]
		position = triangle.mean(axis=0)
		normal = numpy.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
		normal /= numpy.linalg.norm(normal)
		tangent = triangle[1] - triangle[0]
		tangent /= numpy.linalg.norm(tangent)
		origin = position + normal * MINIMUM_INTERSECTION_DISTANCE
		directions, _ = disk_directions((tangent + normal * 0.001) * 149600000000, 695700000, 4096)

		numpy.testing.assert_array_equal(candidate.blocked_rays(origin, directions), reference.blocked_rays(origin, directions))


@pytest.mark.parametrize('face', range(6))
def test_coarse_tiles_keep_float64_when_rounding_can_create_false_self_shadows(face):
	random = numpy.random.default_rng(842 + face)
	heights = random.uniform(-3000, 3000, (17, 17))
	reference = SurfaceMesh((face, 0, 0, 0), heights, 1737400)
	candidate = Open3DSurfaceMesh((face, 0, 0, 0), heights, 1737400)

	assert not candidate.blocks
	assert candidate.maximum_plane_error > MINIMUM_INTERSECTION_DISTANCE / 4

	for _ in range(12):
		row, column = random.integers(0, 16, size=2)
		triangle = reference.triangles(row, column, row + 1, column + 1)[0]
		position = triangle.mean(axis=0)
		normal = numpy.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
		normal /= numpy.linalg.norm(normal)
		tangent = triangle[1] - triangle[0]
		tangent /= numpy.linalg.norm(tangent)
		angles = numpy.linspace(-0.001, 0.001, 257)
		directions = numpy.cos(angles)[:, None] * tangent + numpy.sin(angles)[:, None] * normal
		origin = position + normal * MINIMUM_INTERSECTION_DISTANCE

		numpy.testing.assert_array_equal(candidate.blocked_rays(origin, directions), reference.blocked_rays(origin, directions))


def test_native_ridge_keeps_full_sun_shadow_and_partial_disk_visibility():
	heights = numpy.zeros((17, 17))
	heights[:, 12] = 1000
	reference = SurfaceMesh((0, 6, 32, 32), heights, 1737400)
	candidate = Open3DSurfaceMesh((0, 6, 32, 32), heights, 1737400)
	position = reference.positions[8, 4]
	up = position / numpy.linalg.norm(position)
	east = numpy.cross([0, 0, 1], up)
	east /= numpy.linalg.norm(east)
	triangle = reference.triangles(8, 4, 9, 5)[0]
	normal = numpy.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
	normal /= numpy.linalg.norm(normal)
	fractions = []

	assert candidate.blocks

	for elevation in [1, 1.7, 10]:
		angle = numpy.radians(elevation)
		sun_vector = (numpy.cos(angle) * east + numpy.sin(angle) * up) * 149600000000
		expected = calculate_visibility(reference, position, normal, sun_vector, 695700000)
		actual = calculate_visibility(candidate, position, normal, sun_vector, 695700000)

		assert actual == expected
		fractions.append(actual['visible_sun_fraction'])

	assert fractions[0] == 0
	assert 0 < fractions[1] < 1
	assert fractions[-1] == 1


def test_native_flat_surface_matches_the_analytic_horizon_on_both_sides():
	horizontal, vertical = numpy.meshgrid([-1000.0, 0, 1000], [-1000.0, 0, 1000])
	positions = numpy.stack((horizontal, vertical, numpy.full_like(horizontal, 1737400)), axis=-1)
	block = Open3DSurfaceBlock(positions)
	angles = numpy.radians([-10.0, -1, -0.1, 0, 0.1, 1, 10])
	directions = numpy.column_stack((numpy.cos(angles), numpy.zeros(len(angles)), numpy.sin(angles)))
	origin = numpy.array([0.0, 0, 1737400 + MINIMUM_INTERSECTION_DISTANCE])

	assert block.scene is not None
	numpy.testing.assert_array_equal(block.blocked_rays(origin, directions), angles < 0)
	numpy.testing.assert_array_equal(block.blocked_rays(origin - [0, 0, 0.002], directions), angles > 0)


@pytest.mark.parametrize('row', [0, 16, 32])
def test_shared_tile_vertices_keep_reference_visibility(row):
	heights = numpy.full((33, 33), -4000.0)
	references = [SurfaceMesh((0, 9, tile_x, 256), heights, 1737400) for tile_x in [256, 257]]
	candidates = [Open3DSurfaceMesh((0, 9, tile_x, 256), heights, 1737400) for tile_x in [256, 257]]
	position = references[0].positions[row, -1]
	up = position / numpy.linalg.norm(position)
	east = numpy.cross([0, 0, 1], up)
	east /= numpy.linalg.norm(east)
	origin = position + up * MINIMUM_INTERSECTION_DISTANCE
	directions, _ = disk_directions(east * 149600000000, 695700000, 4096)
	reference_blocked = numpy.zeros(len(directions), dtype=bool)
	candidate_blocked = numpy.zeros(len(directions), dtype=bool)

	numpy.testing.assert_array_equal(position, references[1].positions[row, 0])

	for reference, candidate in zip(references, candidates, strict=True):
		assert candidate.blocks
		reference_blocked |= reference.blocked_rays(origin, directions)
		candidate_blocked |= candidate.blocked_rays(origin, directions)

	numpy.testing.assert_array_equal(candidate_blocked, reference_blocked)
	assert 0 < numpy.mean(~candidate_blocked) < 1
